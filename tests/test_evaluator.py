from gdpr_engine.loader import load_policy
from gdpr_engine.evaluator import evaluate, RequestCtx, Decision

policy = load_policy("tests/fixtures/sample_policy.json")

def test_permit_on_matching_request():
    ctx = RequestCtx(action="use",
                     target="urn:data:customers",
                     purpose="service-improvement")
    assert evaluate(policy, ctx) is Decision.PERMIT

def test_deny_on_wrong_purpose():
    ctx = RequestCtx(action="use",
                     target="urn:data:customers",
                     purpose="marketing")      # not allowed
    assert evaluate(policy, ctx) is Decision.DENY
