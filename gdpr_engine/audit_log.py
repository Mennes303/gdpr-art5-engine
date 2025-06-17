"""
Audit-trail writer for the GDPR-Article-5 engine
-----------------------------------------------

Each call to :func:`write()` appends one **JSON-Lines** entry to
“audit.jsonl”.  Average line size is ~120 bytes, so 1 M requests ≈ 120 MB,
small enough for flat-file retention or ELK/Splunk ingestion.

Top-level fields (all strings):
    • timestamp   – ISO-8601 in UTC
    • policy_uid  – preferred field name
    • policy      – legacy alias for old tests
    • decision    – "Permit" | "Deny" | …
    • action, target, purpose, role – duplicated for compatibility

A nested **ctx** object repeats the request context in one place
(action, target, purpose, role, location, ip).

File is opened line-buffered (`buffering=1`) so each write is atomic on
most OSes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from gdpr_engine.evaluator import RequestCtx

# ---------------------------------------------------------------------
# Log-file location
# ---------------------------------------------------------------------
_LOG = Path(__file__).parent / "audit.jsonl"
_LOG.parent.mkdir(parents=True, exist_ok=True)
_LOG.touch(exist_ok=True)  # ensure the file exists

# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def write(*, policy_uid: str, decision: str, ctx: "RequestCtx") -> None:
    """
    Append one audit record in JSON-Lines format.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # preferred & legacy policy fields
        "policy_uid": policy_uid,
        "policy": policy_uid,  # kept for old test-suite compatibility

        # duplicated simple context fields (legacy tests expect them)
        "action": ctx.action,
        "target": ctx.target,
        "purpose": ctx.purpose,
        "role": ctx.role,

        "decision": decision,

        # modern nested context
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
