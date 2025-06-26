"""
Smoke tests for *sample_policy.json*.

* **Permit** when purpose equals ``service-improvement``.
* **Deny**   when purpose equals ``marketing``.
"""

from gdpr_engine.loader import load_policy
from gdpr_engine.evaluator import evaluate, RequestCtx, Decision

policy = load_policy("tests/fixtures/sample_policy.json")


def test_permit_on_matching_request():
    """Expect **Permit** when request purpose matches the policy."""
    ctx = RequestCtx(action="use", target="urn:data:customers", purpose="service-improvement")
    assert evaluate(policy, ctx) is Decision.PERMIT


def test_deny_on_wrong_purpose():
    """Expect **Deny** when request purpose is not allowed by the policy."""
    ctx = RequestCtx(action="use", target="urn:data:customers", purpose="marketing")
    assert evaluate(policy, ctx) is Decision.DENY
