"""
Unit test: happy‑path check for the ``/decision`` endpoint.

Sends a request that satisfies the sample policy (purpose ``service‑improvement``)
and asserts that the response body contains ``{"decision": "Permit"}``.
"""

from fastapi.testclient import TestClient
from gdpr_engine.api import app

client = TestClient(app)
POLICY = "tests/fixtures/sample_policy.json"


def test_decision_endpoint_permit():
    """Expect **Permit** when the purpose matches the policy."""
    resp = client.post(
        "/decision",
        json={
            "policy_file": POLICY,
            "action": "use",
            "target": "urn:data:customers",
            "purpose": "service-improvement",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"decision": "Permit"}
