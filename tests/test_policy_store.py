import json
from gdpr_engine import policy_store
from gdpr_engine.evaluator import RequestCtx, evaluate, Decision

SAMPLE = {"uid": "urn:test:crud", "permission": []}

def test_crud_roundtrip(tmp_path, monkeypatch):
    # redirect DB into tmp dir
    monkeypatch.setattr(policy_store, "_DB", tmp_path / "p.sqlite3")

    pid = policy_store.create(json.dumps(SAMPLE), uid=SAMPLE["uid"])
    assert pid > 0

    body = json.loads(policy_store.read(pid))
    assert body["uid"] == SAMPLE["uid"]

    body["uid"] = "urn:test:updated"
    policy_store.update(pid, json.dumps(body))

    body2 = json.loads(policy_store.read(pid))
    assert body2["uid"] == "urn:test:updated"

    policy_store.delete(pid)
    try:
        policy_store.read(pid)
        assert False, "should have raised"
    except KeyError:
        pass

def test_decision_with_stored_policy(tmp_path, monkeypatch):
    from gdpr_engine.loader import load_policy
    monkeypatch.setattr(policy_store, "_DB", tmp_path / "p.sqlite3")

    pol_json = {
        "uid": "urn:test:permit",
        "permission": [
            {
                "action": {"name": "use"},
                "target": {"uid": "urn:data:x"}
            }
        ],
    }
    pid = policy_store.create(json.dumps(pol_json), uid=pol_json["uid"])
    policy = load_policy(pid)

    ctx = RequestCtx(action="use", target="urn:data:x")
    assert evaluate(policy, ctx) is Decision.PERMIT
