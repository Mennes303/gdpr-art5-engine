"""
Evaluate a request against a GDPR Article-5 policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from gdpr_engine.model import Policy, Permission, Duty
from gdpr_engine.duty_store import add as add_duty
from gdpr_engine.audit_log import write as audit_write


# ---------------------------------------------------------------------------#
# Decision result                                                             #
# ---------------------------------------------------------------------------#


class Decision(str, Enum):
    PERMIT = "Permit"
    DENY = "Deny"
    NOT_APPLICABLE = "NotApplicable"   # (unused for now)


# ---------------------------------------------------------------------------#
# Request context                                                             #
# ---------------------------------------------------------------------------#


class RequestCtx:
    """
    Minimal request context the PDP evaluates against.

    Fields can be expanded later (IP address, DPO signature, etc.).
    """

    def __init__(
        self,
        *,
        action: str,
        target: str,
        purpose: Optional[str] = None,
        role: Optional[str] = None,
        location: Optional[str] = None,
    ) -> None:
        self.action = action
        self.target = target
        self.purpose = purpose
        self.role = role
        self.location = location          # ISO-3166 alpha-2
        self.timestamp = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------#
# Internal helpers                                                            #
# ---------------------------------------------------------------------------#


def _match_permission(perm: Permission, ctx: RequestCtx) -> bool:
    """Return True if the permission matches the request context."""
    if perm.action.name != ctx.action or perm.target.uid != ctx.target:
        return False
    if perm.constraint:
        return perm.constraint.is_satisfied(ctx=ctx)   # delegate to model
    return True                                        # unconditional


def _record_duty_if_any(perm: Permission, ctx: RequestCtx) -> None:
    """
    If the matched permission has a retention duty (delete after X days),
    insert it into the duty store.
    """
    duty: Duty | None = perm.duty
    if duty and duty.action.name == "delete" and duty.after:
        add_duty(asset_uid=perm.target.uid, after_days=duty.after)


# ---------------------------------------------------------------------------#
# Public API                                                                  #
# ---------------------------------------------------------------------------#


def evaluate(policy: Policy, ctx: RequestCtx) -> Decision:
    """
    Evaluate *ctx* against the given *policy* and return Permit/Deny.

    Side effects:
      • records duties (storage-limitation)
      • appends an audit-trail line
    """
    for perm in policy.permission:
        if _match_permission(perm, ctx):
            _record_duty_if_any(perm, ctx)
            audit_write(policy_uid=policy.uid, decision="Permit", ctx=ctx)
            return Decision.PERMIT

    audit_write(policy_uid=policy.uid, decision="Deny", ctx=ctx)
    return Decision.DENY
