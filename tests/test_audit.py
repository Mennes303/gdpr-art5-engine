"""
Unit test: verify that ``evaluate`` writes exactly one audit entry for a Permit.

The audit file path in ``gdpr_engine.audit_log`` is monkeypatched to a temporary
location so the test does not touch the real log.
"""

import json
from gdpr_engine.model import Action, Asset, Permission, Policy
from gdpr_engine.evaluator import evaluate, RequestCtx, Decision

perm = Permission(action=Action(name="use"), target=Asset(uid="urn:data:x"))
policy = Policy(uid="urn:test:audit", permission=[perm])


def test_audit_line_written(tmp_path, monkeypatch):
    """Expect one **Permit** record with correct fields in the audit log."""
    logfile = tmp_path / "audit.jsonl"
    monkeypatch.setattr("gdpr_engine.audit_log._LOG", logfile)

    ctx = RequestCtx(action="use", target="urn:data:x", purpose="demo")
    assert evaluate(policy, ctx) is Decision.PERMIT

    lines = logfile.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["policy"] == "urn:test:audit"
    assert rec["decision"] == "Permit"
    assert rec["action"] == "use"
