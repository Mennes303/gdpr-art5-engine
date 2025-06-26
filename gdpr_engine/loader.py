"""
Policy loader with memoisation and SQLite integration.

Behaviour
~~~~~~~~~
* ``int`` source → try the SQLite policy store by ID; if missing, fall back to
  ``tests/fixtures/policy-{id}.json`` and insert the fixture into the DB.
* ``str``/``Path`` source → read JSON from disk and upsert it into the store on
  first use.
* Loaded :class:`~gdpr_engine.model.Policy` instances are cached in memory for
  subsequent calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Union, overload

from gdpr_engine import policy_store
from gdpr_engine.model import Policy

_FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
_CACHE: Dict[Union[int, str, Path], Policy] = {}

# Helper functions 

def _upsert_in_store(pid: int, raw: str, uid: str) -> None:
    """Insert raw JSON into the store if not already present."""
    try:
        policy_store.read(pid)
    except KeyError:
        policy_store.create(raw, uid=uid)


def _from_disk(json_path: Path) -> Policy:
    """Load a policy from *json_path* and ensure it is stored in SQLite."""
    raw = json_path.read_text(encoding="utf-8")
    pol = Policy.model_validate_json(raw)
    try:
        pid = int(json_path.stem.split("-")[-1])
    except ValueError:
        return pol  # filename lacks numeric ID
    _upsert_in_store(pid, raw, uid=pol.uid)
    return pol


def _from_store(pid: int) -> Policy:
    """Load a policy from SQLite by ID."""
    raw = policy_store.read(pid)
    return Policy.model_validate_json(raw)


# Public loader 

@overload
def load_policy(src: int) -> Policy: ...

@overload
def load_policy(src: str | Path) -> Policy: ...

def load_policy(src: Union[int, str, Path]) -> Policy:
    """Load a :class:`Policy` by numeric ID or file path."""
    if not isinstance(src, int) and src in _CACHE:
        return _CACHE[src]

    if isinstance(src, int):
        try:
            pol = _from_store(src)
        except KeyError:
            json_path = _FIXTURE_DIR / f"policy-{src}.json"
            if not json_path.exists():
                raise
            pol = _from_disk(json_path)
    else:
        pol = _from_disk(Path(src))

    _CACHE[src] = pol
    return pol
