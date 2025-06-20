"""
Load-test workload for the GDPR-engine
──────────────────────────────────────
We model three scenarios and mark each task with tags so we can pick them
at runtime:

•  burst      – 1 000 VU · 30 s · 90 % read / 10 % write
•  steady     –   100 VU ·  5 min · 95 % read /  5 % write
•  dutyflush  – one scheduler tick while the burst is running

Run examples
────────────
# Smoke-test (10 users, any mix of tasks)
locust -f locustfile.py --headless -u 10 -r 10 -t 10s --host http://localhost:8000

# ❶ Burst profile
locust --tags burst      --headless -u 1000 -r 1000 -t 30s --host http://localhost:8000

# ❷ Steady profile
locust --tags steady     --headless -u 100  -r 25   -t 5m  --host http://localhost:8000

# ❸ Duty-flush (run *while* burst is in progress)
locust --tags dutyflush  --headless -u 1    -r 1    -t 10s --host http://localhost:8000
"""

from random import choice
from locust import HttpUser, task, between, tag

EXAMPLE_POLICY_ID = 1           # change if your seed data differs
SUBJECTS          = ["alice", "bob", "carol"]
DATASET_ID        = "demo-ds-001"
LOCATIONS         = ["DE", "US", "NL", ""]


class EngineUser(HttpUser):
    wait_time = between(0.01, 0.10)   # 10–100 ms “think-time”

    # ── helper methods (to avoid duplication) ──────────────────────────
    def _post_evaluate(self) -> None:
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

    def _post_duty(self) -> None:
        self.client.post(
            "/duties",
            json={
                "policy_id": EXAMPLE_POLICY_ID,
                "subject":   {"id": "scheduler"},
                "duty":      "log-access",          # adapt to your schema
            },
            name="/duties (write)",
        )

    # ───────────────────────────────────────────────────────────────────
    #  B U R S T   (90 % read / 10 % write)
    # ───────────────────────────────────────────────────────────────────
    @task(9)
    @tag("burst", "dutyflush")
    def burst_read(self):
        """High-throughput read during the burst and duty-flush."""
        self._post_evaluate()

    @task(1)
    @tag("burst")
    def burst_write(self):
        """Write load during the burst (≈10 %)."""
        self._post_duty()

    # ───────────────────────────────────────────────────────────────────
    #  S T E A D Y   (95 % read / 5 % write)
    # ───────────────────────────────────────────────────────────────────
    @task(19)
    @tag("steady")
    def steady_read(self):
        """Read-heavy steady-state workload."""
        self._post_evaluate()

    @task(1)
    @tag("steady")
    def steady_write(self):
        """Occasional write during steady-state."""
        self._post_duty()

    # ───────────────────────────────────────────────────────────────────
    #  D U T Y - F L U S H   (scheduler tick)
    # ───────────────────────────────────────────────────────────────────
    @task(1)
    @tag("dutyflush")
    def scheduler_tick(self):
        """
        Trigger the background duty processor while reads are hammering
        the API.  Adjust the endpoint if your implementation differs.
        """
        self.client.post("/duties/flush", name="/duties/flush")
