from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class Policy(BaseModel):
    """Placeholder for ODRL/GDPR policy model."""
    uid: str

class Action(BaseModel):
    name: str

class Permission(BaseModel):
    action: Action
    target: Asset
    constraint: Optional[Constraint] = None
    duty: Optional[Duty] = None

class Asset(BaseModel):
    uid: str

class Constraint(BaseModel):
    left_operand: str
    operator: str = "eq"
    right_operand: str

class Duty(BaseModel):
    action: Action
    constraint: Optional[Constraint] = None