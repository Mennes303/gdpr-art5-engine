"""
FastAPI wrapper around the GDPR Article-5 policy engine.
"""

from __future__ import annotations

from asyncio import create_task, sleep
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gdpr_engine.duty_store import tick as duty_tick
from gdpr_engine.evaluator import Decision, RequestCtx, evaluate
from gdpr_engine.loader import load_policy

# ---------------------------------------------------------------------------#
# Lifespan: start background duty-ticker                                      #
# ---------------------------------------------------------------------------#


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401  (simple docstring fine)
    """
    On startup: launch an async loop that marks overdue duties every hour.
    On shutdown: cancel the loop.
    """

    async def _loop() -> None:
        while True:
            duty_tick()          # scheduled → overdue, if due_at passed
            await sleep(3600)    # tick hourly

    task = create_task(_loop())
    try:
        yield
    finally:
        task.cancel()

# ---------------------------------------------------------------------------#
# FastAPI instance                                                            #
# ---------------------------------------------------------------------------#

app = FastAPI(title="GDPR Article-5 PDP", lifespan=lifespan)

# ---------------------------------------------------------------------------#
# Request / response models                                                   #
# ---------------------------------------------------------------------------#


class DecisionRequest(BaseModel):
    policy_file: str
    action: str
    target: str
    purpose: str | None = None
    role: str | None = None        # enables role-based constraints
    location: str | None = None


class DecisionResponse(BaseModel):
    decision: Decision


# ---------------------------------------------------------------------------#
# Endpoint                                                                    #
# ---------------------------------------------------------------------------#


@app.post("/decision", response_model=DecisionResponse)
def decide(req: DecisionRequest) -> DecisionResponse:
    """
    Evaluate a single request against the given policy file,
    returning Permit / Deny.
    """
    try:
        policy = load_policy(req.policy_file)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    ctx = RequestCtx(
        action=req.action,
        target=req.target,
        purpose=req.purpose,
        role=req.role,
        location=req.location,
    )
    return DecisionResponse(decision=evaluate(policy, ctx))
