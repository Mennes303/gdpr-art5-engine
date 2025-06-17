"""
FastAPI wrapper around the GDPR Article-5 policy engine.

Exposed routes
--------------
POST   /policies           → create, returns {id}
GET    /policies/{id}      → fetch
PUT    /policies/{id}      → replace
DELETE /policies/{id}      → delete
POST   /decision           → Permit / Deny using policy_id *or* policy_file
"""

from __future__ import annotations

import json
from asyncio import create_task, sleep
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gdpr_engine.duty_store import tick as duty_tick
from gdpr_engine.evaluator import Decision, RequestCtx, evaluate
from gdpr_engine.loader import load_policy
from gdpr_engine import policy_store

# ---------------------------------------------------------------------------#
# Lifespan: hourly duty-scheduler                                             #
# ---------------------------------------------------------------------------#


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401
    async def _loop() -> None:
        while True:
            duty_tick()
            await sleep(3600)  # one hour

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
# Policy CRUD models                                                          #
# ---------------------------------------------------------------------------#


class PolicyIn(BaseModel):
    uid: str = Field(..., description="Human-readable unique identifier")
    body: dict = Field(..., description="Raw ODRL/GDPR JSON policy")


class PolicyOut(BaseModel):
    id: int
    uid: str
    body: dict


# ---------------------------------------------------------------------------#
# Decision models                                                             #
# ---------------------------------------------------------------------------#


class DecisionRequest(BaseModel):
    # One of the following must be supplied
    policy_id: Optional[int] = None
    policy_file: Optional[str] = None

    action: str
    target: str
    purpose: str | None = None
    role: str | None = None
    location: str | None = None


class DecisionResponse(BaseModel):
    decision: Decision


# ---------------------------------------------------------------------------#
# /policies endpoints                                                         #
# ---------------------------------------------------------------------------#


@app.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(p: PolicyIn) -> PolicyOut:
    pid = policy_store.create(json.dumps(p.body), uid=p.uid)
    return PolicyOut(id=pid, uid=p.uid, body=p.body)


@app.get("/policies/{pid}", response_model=PolicyOut)
def get_policy(pid: int) -> PolicyOut:
    try:
        body_raw = policy_store.read(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="policy not found")
    body = json.loads(body_raw)
    return PolicyOut(id=pid, uid=body.get("uid", ""), body=body)


@app.put("/policies/{pid}", status_code=204)
def update_policy(pid: int, p: PolicyIn):
    try:
        policy_store.update(pid, json.dumps(p.body))
    except KeyError:
        raise HTTPException(status_code=404, detail="policy not found")


@app.delete("/policies/{pid}", status_code=204)
def delete_policy(pid: int):
    try:
        policy_store.delete(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="policy not found")


# ---------------------------------------------------------------------------#
# /decision endpoint                                                          #
# ---------------------------------------------------------------------------#


@app.post("/decision", response_model=DecisionResponse)
def decide(req: DecisionRequest) -> DecisionResponse:
    """Evaluate a request by policy **ID** _or_ policy file."""
    # --- load policy -----------------------------------------------------
    if req.policy_id is not None:
        try:
            policy = load_policy(req.policy_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="policy id not found")
    elif req.policy_file:
        try:
            policy = load_policy(req.policy_file)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either policy_id or policy_file",
        )

    # --- build context & evaluate ---------------------------------------
    ctx = RequestCtx(
        action=req.action,
        target=req.target,
        purpose=req.purpose,
        role=req.role,
        location=req.location,
    )
    return DecisionResponse(decision=evaluate(policy, ctx))
