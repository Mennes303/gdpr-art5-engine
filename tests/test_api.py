from fastapi.testclient import TestClient
from gdpr_engine.api import app

client = TestClient(app)
POLICY = "tests/fixtures/sample_policy.json"


def test_decision_endpoint_permit():
    """Endpoint should return Permit for a matching purpose."""
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