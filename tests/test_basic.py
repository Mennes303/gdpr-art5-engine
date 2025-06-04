from gdpr_engine.model import Policy, Action, Permission, Asset, Constraint

def test_policy_roundtrip():
    p = Policy(uid="urn:test:1")
    assert p.uid == "urn:test:1"

def test_permission_requires_target():
    action = Action(name="use")
    try:
        Permission(action=action)
    except ValueError:
        assert True
    else:
        assert False, "target is required but was accepted as missing"


def test_constraint_roundtrip():
    perm = Permission(
        action=Action(name="use"),
        target=Asset(uid="urn:data:customers"),
        constraint=Constraint(
            left_operand="purpose",
            operator="eq",
            right_operand="service-improvement"
        )
    )
    dumped = perm.model_dump_json()
    loaded = Permission.model_validate_json(dumped)
    assert loaded == perm