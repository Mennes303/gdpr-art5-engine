"""
Tiny smoke-test for GitHub Actions
──────────────────────────────────
• 90 % of requests hit /evaluate
• 10 % hit /duties
• Payloads are *minimal* examples that already pass FastAPI validation.
Adjust the JSON snippets below if your API schema changes.
"""

from random import choice
from locust import HttpUser, task, between

EXAMPLE_POLICY_ID = 1          # update if your seed data uses other IDs
SUBJECTS          = ["alice", "bob", "carol"]
DATASET_ID        = "demo-ds-001"
LOCATIONS         = ["DE", "US", "NL", ""]

class EngineUser(HttpUser):
    wait_time = between(0.01, 0.1)   # 10-100 ms think-time

    @task(9)                         # ≈ 90 % of the traffic
    def evaluate(self) -> None:
        self.client.post(
            "/evaluate",
            json={
                "policy_id": EXAMPLE_POLICY_ID,
                "subject":   {"id": choice(SUBJECTS)},
                "action":    {"id": "use"},
                "object":    {"id": DATASET_ID},
                "context":   {"location": choice(LOCATIONS)},
            },
            name="/evaluate (read)",
        )

    @task(1)                         # ≈ 10 %
    def create_duty(self) -> None:
        self.client.post(
            "/duties",
            json={
                "policy_id": EXAMPLE_POLICY_ID,
                "subject":   {"id": "scheduler"},
                "duty":      "log-access",    # whatever your endpoint expects
            },
            name="/duties (write)",
        )
