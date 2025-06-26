"""
Audit‑trail module for the GDPR Article‑5 policy engine.

This module maintains an append‑only, tamper‑evident JSON‑Lines log of every
PERMIT / DENY decision and exposes a FastAPI router that returns the complete
ordered audit stream.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List

from fastapi import APIRouter

if TYPE_CHECKING:  # avoid runtime import cycle during type checking
    from gdpr_engine.evaluator import RequestCtx

# Log file setup
_LOG = Path(__file__).with_name("audit.jsonl")
_LOG.parent.mkdir(parents=True, exist_ok=True)  # ensure directory exists
_LOG.touch(exist_ok=True)                       # create file if missing

# FastAPI router
router = APIRouter(tags=["audit"])

@router.get("/", summary="Full ordered audit log")
def full_audit() -> List[dict]:
    """Return every audit entry in write order."""
    with _LOG.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

# Test helpers (pytest only)
def _clear() -> None:  # noqa: D401
    """Truncate the audit log – used by pytest."""
    _LOG.write_text("")

# Public writer
def write(*, policy_uid: str, decision: str, ctx: "RequestCtx") -> None:
    """Append one audit record protected by a hash chain."""

    # core record 
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # policy reference (new and legacy field names)
        "policy_uid": policy_uid,
        "policy": policy_uid,
        # duplicated context for quick grep / SQL import
        "action": ctx.action,
        "target": ctx.target,
        "purpose": ctx.purpose,
        "role": ctx.role,
        "decision": decision,
        # nested context for replay/debugging
        "ctx": {
            "action": ctx.action,
            "target": ctx.target,
            "purpose": ctx.purpose,
            "role": ctx.role,
            "location": getattr(ctx, "location", None),
            "ip": getattr(ctx, "ip", None),
        },
    }

    # integrity fields 
    body_json = json.dumps(record, separators=(",", ":")).encode()
    record["digest"] = hashlib.sha256(body_json).hexdigest()

    try:
        with _LOG.open("rb") as fh:
            last_line = next(reversed(list(fh)))  # last non‑empty line
            prev_chain = json.loads(last_line)["chain"]
    except StopIteration:  # empty file ⇒ genesis entry
        prev_chain = ""

    record["chain"] = hashlib.sha256((prev_chain + record["digest"]).encode()).hexdigest()

    # atomic append 
    with _LOG.open("a", encoding="utf-8", buffering=1) as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
