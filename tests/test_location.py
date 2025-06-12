from gdpr_engine.model import Action, Asset, Permission, Constraint, Policy, Operator
from gdpr_engine.evaluator import RequestCtx, evaluate, Decision

perm_eu_only = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    constraint=Constraint(left_operand="location",
                          operator=Operator.IN,
                          right_operand=["EU"]),
)
policy = Policy(uid="urn:test:loc", permission=[perm_eu_only])


def test_location_permit():
    ctx = RequestCtx(action="use", target="urn:data:customers", location="DE")
    assert evaluate(policy, ctx) is Decision.PERMIT


def test_location_deny():
    ctx = RequestCtx(action="use", target="urn:data:customers", location="US")
    assert evaluate(policy, ctx) is Decision.DENY
