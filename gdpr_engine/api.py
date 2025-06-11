from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gdpr_engine.loader import load_policy
from gdpr_engine.evaluator import RequestCtx, evaluate, Decision

app = FastAPI(title="GDPR Article-5 PDP")


class DecisionRequest(BaseModel):
    policy_file: str
    action: str
    target: str
    purpose: str | None = None


class DecisionResponse(BaseModel):
    decision: Decision


@app.post("/decision", response_model=DecisionResponse)
def decide(req: DecisionRequest) -> DecisionResponse:
    # Load policy (404 if file missing)
    try:
        policy = load_policy(req.policy_file)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Evaluate request
    ctx = RequestCtx(
        action=req.action,
        target=req.target,
        purpose=req.purpose,
    )
    return DecisionResponse(decision=evaluate(policy, ctx))
