"""
FastAPI wrapper around the GDPR Article-5 policy engine.

This module exposes endpoints for policy CRUD operations, policy decision evaluations,
and duty management functionalities. It also integrates an audit log router.
"""

from __future__ import annotations

import json
from asyncio import create_task, sleep
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Engine internals
from gdpr_engine import policy_store
from gdpr_engine.duty_store import (
    tick as duty_tick,
    count_open,
    max_expiry,
    add_overdue,
)
from gdpr_engine.evaluator import Decision, RequestCtx, evaluate
from gdpr_engine.loader import load_policy

# Router for audit log endpoint
from gdpr_engine.audit_log import router as audit_router

# Lifespan manager: executes duty scheduler hourly
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def scheduler_loop() -> None:
        while True:
            duty_tick()
            await sleep(3600)  # Executes hourly

    task = create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()

# FastAPI instance and audit router integration
app = FastAPI(title="GDPR Article-5 PDP", lifespan=lifespan)
app.include_router(audit_router, prefix="/audit", tags=["audit"])

# Pydantic models
class PolicyIn(BaseModel):
    uid: str = Field(..., description="Human-readable unique identifier")
    body: dict = Field(..., description="Raw ODRL/GDPR JSON policy")

class PolicyOut(BaseModel):
    id: int
    uid: str
    body: dict

class DecisionRequest(BaseModel):
    policy_id: Optional[int] = None
    policy_file: Optional[str] = None

    action: str
    target: str
    purpose: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None

class DecisionResponse(BaseModel):
    decision: Decision

# Policy CRUD operations
@app.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(p: PolicyIn) -> PolicyOut:
    pid = policy_store.create(json.dumps(p.body), uid=p.uid)
    return PolicyOut(id=pid, uid=p.uid, body=p.body)

@app.get("/policies/{pid}", response_model=PolicyOut)
def get_policy(pid: int) -> PolicyOut:
    try:
        body_raw = policy_store.read(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="Policy not found")
    body = json.loads(body_raw)
    return PolicyOut(id=pid, uid=body.get("uid", ""), body=body)

@app.put("/policies/{pid}", status_code=204)
def update_policy(pid: int, p: PolicyIn):
    try:
        policy_store.update(pid, json.dumps(p.body))
    except KeyError:
        raise HTTPException(status_code=404, detail="Policy not found")

@app.delete("/policies/{pid}", status_code=204)
def delete_policy(pid: int):
    try:
        policy_store.delete(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="Policy not found")

# Decision evaluation endpoint
@app.post("/decision", response_model=DecisionResponse)
def decide(req: DecisionRequest) -> DecisionResponse:
    if req.policy_id is not None:
        try:
            policy = load_policy(req.policy_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Policy ID not found")
    elif req.policy_file:
        try:
            policy = load_policy(req.policy_file)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    else:
        raise HTTPException(status_code=422, detail="Provide either policy_id or policy_file")

    ctx = RequestCtx(
        action=req.action,
        target=req.target,
        purpose=req.purpose,
        role=req.role,
        location=req.location,
    )
    return DecisionResponse(decision=evaluate(policy, ctx))

# Duty management helpers (for testing and load generation)
@app.post("/duties/flush", status_code=202, tags=["duty"])
def flush_duties() -> dict:
    """Execute the duty scheduler immediately."""
    duty_tick()
    return {"status": "flushed"}

@app.get("/duties/pending", tags=["duty"])
def duties_pending() -> dict:
    """Return the number of open (pending) duties."""
    return {"open": count_open()}

@app.get("/duties/max_expiry", tags=["duty"])
def duties_max_expiry() -> dict:
    """Return the furthest expiry timestamp among pending duties."""
    ts = max_expiry()
    return {"ts": ts or 0}

@app.post("/duties/schedule", status_code=201, tags=["duty"])
def duties_schedule(asset_uid: str = "urn:data:test") -> dict:
    """Insert a synthetic duty with an overdue timestamp (for testing)."""
    add_overdue(asset_uid)
    return {"scheduled": True}
