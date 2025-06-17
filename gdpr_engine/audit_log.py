"""
Audit-trail writer for the GDPR-Article-5 engine
-----------------------------------------------

Every call to :func:`write()` appends exactly one **JSON line** to
“audit.jsonl”.  Each entry is ~120 bytes, so one million requests take
≈120 MB – small enough for flat-file retention and easy to ingest into
ELK, Splunk, etc.

Field layout (all strings):
    • timestamp   – ISO-8601 in UTC
    • policy_uid  – UID of the policy that produced the decision
    • decision    – "Permit" | "Deny" | …
    • ctx         – minimal request context (action, target, purpose, role, location, ip)

The file is opened with *line buffering* (`buffering=1`) so each write
is atomic on most OSes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:                     # pragma: no cover
    from gdpr_engine.evaluator import RequestCtx

# ---------------------------------------------------------------------
# Log file location
# ---------------------------------------------------------------------
_LOG = Path(__file__).parent / "audit.jsonl"
_LOG.parent.mkdir(parents=True, exist_ok=True)
_LOG.touch(exist_ok=True)             # ensure the file exists

# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def write(*, policy_uid: str, decision: str, ctx: "RequestCtx") -> None:
    """
    Append one audit record in JSON-Lines format.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policy_uid": policy_uid,
        "decision": decision,
        "ctx": {
            "action": ctx.action,
            "target": ctx.target,
            "purpose": ctx.purpose,
            "role": ctx.role,
            "location": getattr(ctx, "location", None),
            "ip": getattr(ctx, "ip", None),  # future-proof
        },
    }

    # line-buffered write → flushes after every newline
    with _LOG.open("a", encoding="utf-8", buffering=1) as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
