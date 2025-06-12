from datetime import datetime, timezone, timedelta
from gdpr_engine.model import Action, Asset, Permission, Duty, Policy
from gdpr_engine.evaluator import evaluate, RequestCtx, Decision
from gdpr_engine.duty_store import list_all, tick

perm = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    duty=Duty(action=Action(name="delete"), after=1),
)
policy = Policy(uid="urn:test:duty", permission=[perm])


def test_duty_record_and_tick():
    # Permit the request → duty gets recorded
    ctx = RequestCtx(action="use", target="urn:data:customers")
    assert evaluate(policy, ctx) is Decision.PERMIT

    duties = list(list_all())
    assert duties, "duty not recorded"
    duty_id, asset, due_at, state = duties[-1]
    assert state == "scheduled"

    # Fast-forward 2 days and run manual tick
    future = datetime.now(timezone.utc) + timedelta(days=2)
    tick(now=future)

    duty_id, asset, due_at, state = list_all()[-1]
    assert state == "overdue"
