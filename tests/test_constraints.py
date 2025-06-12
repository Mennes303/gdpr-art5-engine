"""
Unit-tests for the extended Constraint logic:
  • purpose IN [...]
  • role == ...
  • dateTime BETWEEN start/end
"""

from datetime import datetime, timezone, timedelta

from gdpr_engine.model import (
    Action,
    Asset,
    Permission,
    Constraint,
    Operator,
    Policy,
)
from gdpr_engine.evaluator import RequestCtx, evaluate, Decision

# --------------------------------------------------------------------------- #
# purpose IN list                                                             #
# --------------------------------------------------------------------------- #

perm_purpose_list = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    constraint=Constraint(
        left_operand="purpose",
        operator=Operator.IN,
        right_operand=["research", "service-improvement"],
    ),
)
policy_purpose = Policy(uid="urn:test:purpose", permission=[perm_purpose_list])


def test_purpose_in_permit():
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
        purpose="research",
    )
    assert evaluate(policy_purpose, ctx) is Decision.PERMIT


def test_purpose_in_deny():
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
        purpose="marketing",
    )
    assert evaluate(policy_purpose, ctx) is Decision.DENY


# --------------------------------------------------------------------------- #
# role EQ                                                                     #
# --------------------------------------------------------------------------- #

perm_role = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    constraint=Constraint(
        left_operand="role",
        operator=Operator.EQ,
        right_operand="data-analyst",
    ),
)
policy_role = Policy(uid="urn:test:role", permission=[perm_role])


def test_role_eq_permit():
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
        role="data-analyst",
    )
    assert evaluate(policy_role, ctx) is Decision.PERMIT


def test_role_eq_deny():
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
        role="intern",
    )
    assert evaluate(policy_role, ctx) is Decision.DENY


# --------------------------------------------------------------------------- #
# dateTime BETWEEN (today)                                                    #
# --------------------------------------------------------------------------- #

today_iso = datetime.now(timezone.utc).date().isoformat()
perm_date_between = Permission(
    action=Action(name="use"),
    target=Asset(uid="urn:data:customers"),
    constraint=Constraint(
        left_operand="dateTime",
        operator=Operator.BETWEEN,
        right_operand=f"{today_iso}/{today_iso}",
    ),
)
policy_date = Policy(uid="urn:test:date", permission=[perm_date_between])


def test_date_between_permit():
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
    )
    assert evaluate(policy_date, ctx) is Decision.PERMIT


def test_date_between_deny_after():
    # Advance 2 days to fall outside the range
    future = datetime.now(timezone.utc) + timedelta(days=2)
    ctx = RequestCtx(
        action="use",
        target="urn:data:customers",
    )
    # Monkey-patch timestamp for this check
    ctx.timestamp = future
    assert evaluate(policy_date, ctx) is Decision.DENY
