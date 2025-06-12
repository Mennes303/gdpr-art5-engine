from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
import json


if TYPE_CHECKING:                       # pragma: no cover
    from gdpr_engine.evaluator import RequestCtx

_LOG = Path(__file__).parent / "audit.jsonl"
_LOG.touch(exist_ok=True)  # ensure file exists


def write(
    *,
    policy_uid: str,
    decision: str,
    ctx: "RequestCtx",
) -> None:
    """
    Append one audit record as JSONL.  Each line ~120 bytes → 1 M lines ≈ 120 MB.
    Suitable for flat-file retention or ingestion into ELK/Splunk later.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "policy": policy_uid,
        "decision": decision,
        "action": ctx.action,
        "target": ctx.target,
        "purpose": ctx.purpose,
        "role": ctx.role,
        "ip": getattr(ctx, "ip", None),  # future-proof
    }
    # Use line buffering so each write is atomic on most OSes
    with _LOG.open("a", encoding="utf-8", buffering=1) as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
