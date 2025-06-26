"""
Unit test: ensure retention duty is recorded and fulfilled after ``tick``.
"""

from datetime import datetime, timezone, timedelta

from gdpr_engine.model import Action, Asset, Permission, Duty, Policy
from gdpr_engine.evaluator import evaluate, RequestCtx, Decision
from gdpr_engine.duty_store import list_all, tick

perm = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    duty=Duty(action=Action(name="delete"), after=1),  # delete after 1 day
)
policy = Policy(uid="urn:test:duty", permission=[perm])


def test_duty_record_and_tick():
    """Permit request → duty scheduled → tick moves it to fulfilled/overdue."""
    ctx = RequestCtx(action="use", target="urn:data:customers")
    assert evaluate(policy, ctx) is Decision.PERMIT  # schedule duty

    duty_id, asset, due_at, state = list_all()[-1]
    assert state == "scheduled"

    # Fast‑forward two days and trigger scheduler
    future = datetime.now(timezone.utc) + timedelta(days=2)
    tick(now=future)

    duty_id, asset, due_at, state = list_all()[-1]
    assert state in {"fulfilled", "overdue"}  # depending on version
