"""
Load-test script for the GDPR engine API.

Default behaviour = 90 % read-only evaluate requests,
10 % write requests that add a duty.
You can tweak the ratio at runtime:

    READ_RATIO=0.95 locust -f locustfile.py …

All users share the same asset UID to keep the script tiny; feel free
to randomise if you want a heavier write pattern.
"""

from locust import HttpUser, task, between
import random, os

# Read / write mix — can be overridden with an env variable
READ_RATIO = float(os.getenv("READ_RATIO", "0.90"))

class EngineUser(HttpUser):
    host = os.getenv("LOCUST_HOST") or "http://localhost:8000"
    wait_time = between(0.05, 0.2)          # ✱ realistic “think time”

    @task
    def evaluate_or_insert(self) -> None:
        """90 % evaluate, 10 % create-duty by default."""
        if random.random() < READ_RATIO:
            self.client.post(
                "/evaluate",
                json={
                    "action": "use",
                    "asset_uid": "urn:data:customers",
                    "purpose": "service-improvement",
                },
                name="/evaluate (read)",
            )
        else:
            self.client.post(
                "/duties",
                json={
                    "asset_uid": "urn:data:customers",
                    "after_days": 30,
                },
                name="/duties (write)",
            )
