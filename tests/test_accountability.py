"""
End‑to‑end accountability test for the PDP API.

Steps
-----
1. Seed *n* synthetic ``/decision`` requests so the audit log is non‑trivial.
2. Verify the SHA‑256 hash chain across all audit entries.
3. Advance the duty scheduler (via ``/duties/flush``) until it stops writing.
   Assert that at least one ``Delete`` record appears.

Change ``BASE`` if your server is listening elsewhere.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from freezegun import freeze_time

BASE = "http://127.0.0.1:8000"  # adapt as needed
PATH_DECIDE = "/decision"


# Helper functions


def _audit_entries() -> list[dict]:
    return requests.get(f"{BASE}/audit/").json()


def _terminal_hash(entries: list[dict]) -> str:
    h = ""
    for e in entries:
        h = hashlib.sha256((h + e["digest"]).encode()).hexdigest()
    return h


def _tick_scheduler() -> None:
    requests.post(f"{BASE}/duties/flush", timeout=5).raise_for_status()


def _seed_decisions(n: int = 100) -> None:
    """Fire *n* synthetic decision requests with varying targets."""
    template = {
        "policy_id": 1,
        "policy_file": "default.pol.json",
        "action": "read",
        "purpose": "research",
        "role": "agent",
        "location": "nl",
    }
    for i in range(n):
        body = {**template, "target": f"sensor_{i % 10}"}
        resp = requests.post(f"{BASE}{PATH_DECIDE}", json=body, timeout=5)
        resp.raise_for_status()



# Single test


@pytest.mark.timeout(120)
def test_accountability() -> None:
    # 1. Seed traffic 
    _seed_decisions(100)

    # 2. Verify hash chain 
    entries = _audit_entries()
    assert entries, "audit log is unexpectedly empty"
    assert _terminal_hash(entries) == entries[-1]["chain"]

    # 3. Duty replay 
    before_len = len(entries)
    now = datetime.now(timezone.utc)

    with freeze_time(now) as frozen:
        for _ in range(400):
            _tick_scheduler()
            time.sleep(0.05)
            after_entries = _audit_entries()
            if len(after_entries) == before_len:
                break  # converged
            before_len = len(after_entries)
            frozen.move_to(frozen.time_to_freeze + timedelta(days=1))
        else:
            pytest.fail("duties still pending after 400 scheduler ticks")

        deletes_logged = sum(1 for e in after_entries if e.get("decision") == "Delete")
        print(f"\n[AUDIT] total entries = {len(after_entries)}")
        print(f"[DUTY ] deletes logged = {deletes_logged}")
        assert deletes_logged > 0, "no deletes were executed or logged"
