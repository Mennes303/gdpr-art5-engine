"""
Policy loader.

* If given an **int** → read JSON from SQLite (policy_store).
* If given a **str/Path** → read JSON file from disk.
* Results are cached in-memory for speed.
"""

from __future__ import annotations


from pathlib import Path
from typing import Union, Dict

from gdpr_engine.model import Policy
from gdpr_engine import policy_store

# ---------------------------------------------------------------------------#
# Cache                                                                       #
# ---------------------------------------------------------------------------#

_CACHE: Dict[Union[int, str, Path], Policy] = {}

# ---------------------------------------------------------------------------#
# Helpers                                                                     #
# ---------------------------------------------------------------------------#


def _from_file(path: str | Path) -> Policy:
    text = Path(path).read_text(encoding="utf-8")
    return Policy.model_validate_json(text)


def _from_store(pid: int) -> Policy:
    body = policy_store.read(pid)           # returns raw JSON string
    return Policy.model_validate_json(body)


# ---------------------------------------------------------------------------#
# Public loader                                                               #
# ---------------------------------------------------------------------------#


def load_policy(src: Union[int, str, Path]) -> Policy:
    """
    Load a policy by **database ID** *or* by **file path*.
    ID takes precedence if `src` is an `int`.

    Results are memoised so repeated loads are fast.
    """
    if src in _CACHE:
        return _CACHE[src]

    if isinstance(src, int):
        pol = _from_store(src)
    else:
        pol = _from_file(src)

    _CACHE[src] = pol
    return pol
