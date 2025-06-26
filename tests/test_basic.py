"""
Unit tests for model validation and round-trips.
"""

from gdpr_engine.model import (
    Policy,
    Action,
    Permission,
    Asset,
    Constraint,
    Operator,  # enum used to silence type-checker warnings
)


def test_policy_roundtrip():
    """Policy should preserve the provided UID."""
    p = Policy(uid="urn:test:1")
    assert p.uid == "urn:test:1"


def test_permission_requires_target():
    """Omitting *target* when instantiating Permission must raise ``ValueError``."""
    action = Action(name="use")
    try:
        Permission(action=action)  # type: ignore[arg-type]
    except ValueError:
        assert True
    else:
        assert False, "target missing but accepted"


def test_constraint_roundtrip():
    """Serialise/deserialise a permission with constraint and ensure equality."""
    perm = Permission(
        action=Action(name="use"),
        target=Asset(uid="urn:data:customers"),
        constraint=Constraint(
            left_operand="purpose",
            operator=Operator.EQ,  
            right_operand="service-improvement",
        ),
    )
    dumped = perm.model_dump_json()
    loaded = Permission.model_validate_json(dumped)
    assert loaded == perm