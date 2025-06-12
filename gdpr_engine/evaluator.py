"""
Evaluator — turns (Policy, RequestCtx) into a Decision.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from gdpr_engine.model import Policy, Permission
from gdpr_engine.duty_store import add as add_duty
from gdpr_engine.audit_log import write as audit_write


# ---------------------------------------------------------------------------#
# Decision enum                                                               #
# ---------------------------------------------------------------------------#


class Decision(str, Enum):
    PERMIT = "Permit"
    DENY = "Deny"
    NOT_APPLICABLE = "NotApplicable"


# ---------------------------------------------------------------------------#
# Request context                                                             #
# ---------------------------------------------------------------------------#


class RequestCtx:
    """
    Minimal request context.

    Extend with caller IP, region, etc. as your engine grows.
    """

    def __init__(
        self,
        *,
        action: str,
        target: str,
        purpose: Optional[str] = None,
        role: Optional[str] = None,
    ):
        self.action = action
        self.target = target
        self.purpose = purpose
        self.role = role
        # timezone-aware timestamp, required for constraint.dateTime checks
        self.timestamp = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------#
# Internal helpers                                                            #
# ---------------------------------------------------------------------------#


def _match_permission(perm: Permission, ctx: RequestCtx) -> bool:
    """Return True if this permission applies to the request context."""
    if perm.action.name != ctx.action or perm.target.uid != ctx.target:
        return False

    # If there is a constraint, delegate evaluation to its helper
    if perm.constraint:
        return perm.constraint.is_satisfied(ctx=ctx)

    # Unconstrained permission ⇒ match
    return True


# ---------------------------------------------------------------------------#
# Public API                                                                  #
# ---------------------------------------------------------------------------#


def evaluate(policy: Policy, ctx: RequestCtx) -> Decision:
    """
    Iterate over policy permissions until one matches.
    Return PERMIT / DENY (no NOT_APPLICABLE yet).
    """
    for perm in policy.permission:
        if _match_permission(perm, ctx):
            # Record any storage-limitations duties
            if perm.duty and perm.duty.action.name == "delete" and perm.duty.after:
                add_duty(asset_uid=perm.target.uid, after_days=perm.duty.after)
            audit_write(policy_uid=policy.uid, decision="Permit", ctx=ctx)
            return Decision.PERMIT
    audit_write(policy_uid=policy.uid, decision="Deny", ctx=ctx)
    return Decision.DENY
