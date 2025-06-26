"""
Core data‑model classes for the GDPR Article‑5 policy engine.

Includes:
* **Action**, **Asset**, **Constraint**, **Duty**, **Permission**, **Policy**
* Helper for region expansion (``EU`` → ISO‑codes) and ISO datetime parsing.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import lru_cache
from typing import List, Optional, TYPE_CHECKING

from dateutil import parser as dtparse
from pydantic import BaseModel


# Helper functions

def _parse_iso(value: str) -> datetime:
    """Return an aware UTC datetime for *value* (date or full ISO string)."""
    dt = dtparse.parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# Region aliases
_REGION: dict[str, set[str]] = {
    "EU": {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    }
}

@lru_cache(maxsize=None)
def _expand_countries(values: tuple[str, ...]) -> set[str]:
    """Replace region keywords (e.g. ``EU``) with concrete ISO codes."""
    out: set[str] = set()
    for v in values:
        v_up = v.upper()
        out |= _REGION.get(v_up, {v_up})
    return out


# Enums

class Operator(str, Enum):
    EQ = "eq"
    IN = "in"
    NOT_IN = "not in"
    BEFORE = "before"
    AFTER = "after"
    BETWEEN = "between"  # "start/end"


# Core model classes


class Action(BaseModel):
    name: str

class Asset(BaseModel):
    uid: str

class Constraint(BaseModel):
    """Boolean expression ``left_operand OP right_operand``."""

    left_operand: str
    operator: Operator = Operator.EQ
    right_operand: str | List[str]

    def is_satisfied(self, *, ctx: "RequestCtx") -> bool:  # noqa: D401
        match self.left_operand:
            # Purpose
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
            # Role
            case "role":
                if self.operator in {Operator.EQ, Operator.IN}:
                    roles = (
                        self.right_operand
                        if isinstance(self.right_operand, list)
                        else [r.strip() for r in str(self.right_operand).split(",")]
                    )
                    return ctx.role in roles
            # Location 
            case "location":
                loc = (ctx.location or "").upper()
                allowed_set = _expand_countries(
                    tuple(
                        self.right_operand
                        if isinstance(self.right_operand, list)
                        else [s.strip() for s in str(self.right_operand).split(",")]
                    )
                )
                if self.operator in {Operator.EQ, Operator.IN}:
                    return loc in allowed_set
                if self.operator is Operator.NOT_IN:
                    return loc not in allowed_set
            # DateTime 
            case "dateTime":
                now = ctx.timestamp
                if self.operator is Operator.BEFORE:
                    return now < _parse_iso(str(self.right_operand))
                if self.operator is Operator.AFTER:
                    return now > _parse_iso(str(self.right_operand))
                if self.operator is Operator.BETWEEN:
                    start_s, end_s = str(self.right_operand).split("/")
                    start = _parse_iso(start_s)
                    end = _parse_iso(end_s)
                    if (
                        start.time() == datetime.min.time()
                        and end.time() == datetime.min.time()
                        and start.date() == end.date()
                    ):
                        end += timedelta(days=1)
                    return start <= now <= end
        return False  # unsupported combination

class Duty(BaseModel):
    action: Action
    after: Optional[int] = None  # retention in days
    constraint: Optional[Constraint] = None

class Permission(BaseModel):
    action: Action
    target: Asset
    constraint: Optional[Constraint] = None
    duty: Optional[Duty] = None

class Policy(BaseModel):
    uid: str
    permission: List[Permission] = []


# Forward reference for RequestCtx (typing only)

if TYPE_CHECKING:  # pragma: no cover
    from gdpr_engine.evaluator import RequestCtx
