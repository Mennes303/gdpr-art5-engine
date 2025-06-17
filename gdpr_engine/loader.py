"""
Policy loader.

* If given an **int** → try the SQLite store first; if that fails,
  fall back to tests/fixtures/policy-{id}.json (and insert it into the DB).
* If given a **str/Path** → read the JSON file from disk (and insert/update
  the DB the first time it is seen).
* Loaded `Policy` objects are cached in-memory for speed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Union, overload

from gdpr_engine import policy_store
from gdpr_engine.model import Policy

# ---------------------------------------------------------------------------#
# Configuration & cache                                                      #
# ---------------------------------------------------------------------------#

_FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
_CACHE: Dict[Union[int, str, Path], Policy] = {}

# ---------------------------------------------------------------------------#
# Helpers                                                                     #
# ---------------------------------------------------------------------------#


def _upsert_in_store(pid: int, raw: str, uid: str) -> None:
    """Insert JSON in the DB if it is not there yet, otherwise keep existing."""
    try:
        policy_store.read(pid)  # already present?
    except KeyError:
        policy_store.create(raw, uid=uid)  # first time: insert
    # (we deliberately *don’t* update if it already exists – keeps tests idempotent)


def _from_disk(json_path: Path) -> Policy:
    """Read, validate, and make sure it lives in the DB."""
    raw = json_path.read_text(encoding="utf-8")
    pol = Policy.model_validate_json(raw)
    # Derive the numeric ID from the filename, e.g.  policy-1.json  -> 1
    try:
        pid = int(json_path.stem.split("-")[-1])
    except ValueError:
        # Filename does not encode an ID; still return the Policy object
        return pol

    _upsert_in_store(pid, raw, uid=pol.uid)
    return pol


def _from_store(pid: int) -> Policy:
    """Read JSON from SQLite and return a validated Policy object."""
    raw = policy_store.read(pid)  # may raise KeyError
    return Policy.model_validate_json(raw)


# ---------------------------------------------------------------------------#
# Public loader                                                               #
# ---------------------------------------------------------------------------#

@overload
def load_policy(src: int) -> Policy: ...
@overload
def load_policy(src: str | Path) -> Policy: ...


def load_policy(src: Union[int, str, Path]) -> Policy:
    """
    Load a policy by **database ID** *or* by **file path**.

    * `int` → DB first, fixture fallback.
    * `str`/`Path` → load from file (and record in DB the first time).

    Results are memoised so repeated loads are fast.
    """
    if not isinstance(src, int) and src in _CACHE:
        return _CACHE[src]

    # ------------------------------------------------------------------#
    # Case 1: numeric ID                                                 #
    # ------------------------------------------------------------------#
    if isinstance(src, int):
        try:
            pol = _from_store(src)
        except KeyError:
            json_path = _FIXTURE_DIR / f"policy-{src}.json"
            if not json_path.exists():
                raise  # keep original KeyError behaviour
            pol = _from_disk(json_path)

    # ------------------------------------------------------------------#
    # Case 2: explicit pathname                                          #
    # ------------------------------------------------------------------#
    else:
        pol = _from_disk(Path(src))

    _CACHE[src] = pol
    return pol
