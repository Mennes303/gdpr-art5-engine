"""
Load-test workload for the GDPR-Article-5 engine.

Scenarios (select with --tags):
• burst      – 1 000 VU · 30 s · 90 % read / 10 % write
• steady     –   100 VU · 5 min · 95 % read /  5 % write
• dutyflush  – fire scheduler tick while the burst is running
• flush      – alias for dutyflush (same behaviour, more concise CLI)
"""

from __future__ import annotations

from random import choice
from typing import List, Optional

import requests
from locust import FastHttpUser, between, events, tag, task

# ---------------------------------------------------------------------------#
# Constant test data (tweak to taste)                                        #
# ---------------------------------------------------------------------------#
READ_ONLY_POLICY_ID: int = 1        # shipped in the sample DB
TARGET: str = "urn:data:customers"
ACTION: str = "use"
LOCATIONS: List[str] = ["DE", "US", "NL", "FR", "BR"]

# This will be filled once _seed_duty_policy() runs
DUTY_POLICY_ID: Optional[int] = None


# ---------------------------------------------------------------------------#
# Helper functions that issue HTTP calls                                     #
# ---------------------------------------------------------------------------#
def _post_read(client):
    client.post(
        "/decision",
        json={
            "policy_id": READ_ONLY_POLICY_ID,
            "action": ACTION,
            "target": TARGET,
            "location": choice(LOCATIONS),
        },
        name="/decision (read)",
    )


def _post_write(client):
    """Query against the policy that contains a duty clause."""
    if DUTY_POLICY_ID is None:
        # Fallback: treat as read if seeding somehow failed
        _post_read(client)
        return

    client.post(
        "/decision",
        json={
            "policy_id": DUTY_POLICY_ID,
            "action": ACTION,
            "target": TARGET,
        },
        name="/decision (write-duty)",
    )


# ---------------------------------------------------------------------------#
# Locust user model                                                          #
# ---------------------------------------------------------------------------#
class EngineUser(FastHttpUser):
    wait_time = between(0.01, 0.10)  # 10–100 ms think-time

    # ── Burst (90 % read / 10 % write) ────────────────────────────────────
    @task(9)
    @tag("burst", "dutyflush", "flush")   # added "flush"
    def burst_read(self):
        _post_read(self.client)

    @task(1)
    @tag("burst")
    def burst_write(self):
        _post_write(self.client)

    # ── Steady (95 % read / 5 % write) ───────────────────────────────────
    @task(19)
    @tag("steady")
    def steady_read(self):
        _post_read(self.client)

    @task(1)
    @tag("steady")
    def steady_write(self):
        _post_write(self.client)

    # ── Duty-flush: kick the scheduler once ──────────────────────────────
    @task(1)
    @tag("dutyflush", "flush")            # added "flush"
    def scheduler_tick(self):
        self.client.post("/duties/flush", name="/duties/flush")


# ---------------------------------------------------------------------------#
# One-time setup: create a policy that has a duty clause                     #
# ---------------------------------------------------------------------------#
@events.test_start.add_listener
def _seed_duty_policy(environment, **kw):
    """
    Create a fresh policy that defines a duty so every evaluation writes one
    row. Store the returned id in DUTY_POLICY_ID so all users can use it.
    """
    global DUTY_POLICY_ID

    policy_body = {
        "uid": "urn:policy:duty-loadtest",            # ← uid now inside body
        "permission": [
            {
                "action": {"name": ACTION},
                "target": {"uid": TARGET},
                "duty": {                             # ← single OBJECT
                    "action": {"name": "delete"},
                    "after": 365
                },
            }
        ],
    }

    url = f"{environment.parsed_options.host}/policies"
    try:
        resp = requests.post(
            url,
            json={"uid": "urn:policy:duty-loadtest", "body": policy_body},
            timeout=5,
        )
        resp.raise_for_status()
        DUTY_POLICY_ID = resp.json()["id"]
        print(f"[seed] duty policy created with id={DUTY_POLICY_ID}")
    except requests.HTTPError as exc:
        print(f"[seed] ERROR creating duty policy: {exc}")
        DUTY_POLICY_ID = None
