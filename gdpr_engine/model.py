"""
Core data-model classes for the GDPR Article-5 policy engine.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import List, Optional, TYPE_CHECKING

from dateutil import parser as dtparse
from pydantic import BaseModel


# ---------------------------------------------------------------------------#
# Utility                                                                     #
# ---------------------------------------------------------------------------#


def _parse_iso(value: str) -> datetime:
    """
    Return an *aware* UTC datetime for either:
      • date-only  (YYYY-MM-DD)
      • full ISO datetime (with or without tz)
    """
    dt = dtparse.parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)         # assume UTC for naïve
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------#
# Enums                                                                       #
# ---------------------------------------------------------------------------#


class Operator(str, Enum):
    EQ = "eq"
    IN = "in"
    BEFORE = "before"
    AFTER = "after"
    BETWEEN = "between"          # "start/end"


# ---------------------------------------------------------------------------#
# Core model classes                                                          #
# ---------------------------------------------------------------------------#


class Action(BaseModel):
    name: str


class Asset(BaseModel):
    uid: str


class Constraint(BaseModel):
    """
    Boolean restriction of the form `left_operand OP right_operand`.
    Supported operands:
      • purpose  (eq, in)
      • role     (eq, in)
      • dateTime (before, after, between)
    """

    left_operand: str
    operator: Operator = Operator.EQ
    right_operand: str | List[str]

    # ---------------------------------------------------------------------#
    # Evaluation                                                            #
    # ---------------------------------------------------------------------#
    def is_satisfied(self, *, ctx: "RequestCtx") -> bool:  # quoted fwd-ref
        match self.left_operand:
            # ----- purpose ------------------------------------------------
            case "purpose":
                if self.operator is Operator.EQ:
                    return ctx.purpose == self.right_operand
                if self.operator is Operator.IN:
                    allowed = (
                        self.right_operand
                        if isinstance(self.right_operand, list)
                        else [s.strip() for s in str(self.right_operand).split(",")]
                    )
                    return ctx.purpose in allowed

            # ----- role ---------------------------------------------------
            case "role":
                if self.operator in (Operator.EQ, Operator.IN):
                    roles = (
                        self.right_operand
                        if isinstance(self.right_operand, list)
                        else [r.strip() for r in str(self.right_operand).split(",")]
                    )
                    return ctx.role in roles

            # ----- dateTime -----------------------------------------------
            case "dateTime":
                now = ctx.timestamp  # aware UTC
                if self.operator is Operator.BEFORE:
                    return now < _parse_iso(str(self.right_operand))
                if self.operator is Operator.AFTER:
                    return now > _parse_iso(str(self.right_operand))
                if self.operator is Operator.BETWEEN:
                    start_s, end_s = str(self.right_operand).split("/")
                    start = _parse_iso(start_s)
                    end = _parse_iso(end_s)

                    # date-only "YYYY-MM-DD/YYYY-MM-DD" (same day) → full day
                    if (
                        start.time() == datetime.min.time()
                        and end.time() == datetime.min.time()
                        and start.date() == end.date()
                    ):
                        end += timedelta(days=1)

                    return start <= now <= end

        # unsupported operand/operator
        return False


class Duty(BaseModel):
    action: Action
    constraint: Optional[Constraint] = None


class Permission(BaseModel):
    action: Action
    target: Asset
    constraint: Optional[Constraint] = None
    duty: Optional[Duty] = None


class Policy(BaseModel):
    uid: str
    permission: List[Permission] = []


# ---------------------------------------------------------------------------#
# Forward reference for RequestCtx (typing only)                              #
# ---------------------------------------------------------------------------#

if TYPE_CHECKING:  # pragma: no cover
    from gdpr_engine.evaluator import RequestCtx
