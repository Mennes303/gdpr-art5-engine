"""
Locust workload definitions for the GDPR Article‑5 PDP.

Available tags (choose with ``--tags``):
* **burst**     – 1 000 VUs · 30 s · 90 % read / 10 % write
* **steady**    –   100 VUs · 5 min · 95 % read /  5 % write
* **dutyflush** – same as *burst* plus a scheduler flush during the run
* **flush**     – alias for *dutyflush* (shorter CLI)
"""

from __future__ import annotations

from random import choice
from typing import List, Optional

import requests
from locust import FastHttpUser, between, events, tag, task

# Static test data
READ_ONLY_POLICY_ID = 1  # fixture shipped in sample DB
TARGET = "urn:data:customers"
ACTION = "use"
LOCATIONS: List[str] = ["DE", "US", "NL", "FR", "BR"]

# This will be set once the duty‑policy is seeded
DUTY_POLICY_ID: Optional[int] = None


# Helper functions

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
    """Send a request that triggers a retention duty."""
    if DUTY_POLICY_ID is None:  # seeding failed ⇒ fall back to read‑only
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


# User model 
class EngineUser(FastHttpUser):
    wait_time = between(0.01, 0.10)  # 10–100 ms think time

    # Burst profile – 90 % read / 10 % write
    @task(9)
    @tag("burst", "dutyflush", "flush")
    def burst_read(self):
        _post_read(self.client)

    @task(1)
    @tag("burst")
    def burst_write(self):
        _post_write(self.client)

    # Steady profile – 95 % read / 5 % write
    @task(19)
    @tag("steady")
    def steady_read(self):
        _post_read(self.client)

    @task(1)
    @tag("steady")
    def steady_write(self):
        _post_write(self.client)

    # Duty‑flush: one‑off scheduler tick
    @task(1)
    @tag("dutyflush", "flush")
    def scheduler_tick(self):
        self.client.post("/duties/flush", name="/duties/flush")


# One‑time seeding: create a policy containing a duty 
@events.test_start.add_listener
def _seed_duty_policy(environment, **_):
    global DUTY_POLICY_ID

    policy_body = {
        "uid": "urn:policy:duty-loadtest",
        "permission": [
            {
                "action": {"name": ACTION},
                "target": {"uid": TARGET},
                "duty": {"action": {"name": "delete"}, "after": 1},
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
