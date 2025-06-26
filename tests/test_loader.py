"""
Unit test: verify that ``load_policy`` correctly parses *sample_policy.json*.
"""

from gdpr_engine.loader import load_policy


def test_loader_roundtrip():
    """Loaded policy should expose expected UID and first action name."""
    policy = load_policy("tests/fixtures/sample_policy.json")
    assert policy.uid == "urn:policy:demo:1"
    assert policy.permission[0].action.name == "use"
