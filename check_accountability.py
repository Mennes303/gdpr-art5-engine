"""
Quick standalone script: replay *corpus.csv* through the evaluator, redirect the
audit log to a temp file, and verify that every request generates exactly one
well‑formed audit line.
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from gdpr_engine.audit_log import _LOG as _AUDIT_LOG_PATH
from gdpr_engine import audit_log
from gdpr_engine.evaluator import RequestCtx, evaluate
from gdpr_engine.loader import load_policy

CORPUS = Path("tests") / "corpus.csv"  # adjust if moved

# 1. Redirect audit log to a temporary file
_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
audit_log._LOG = Path(_tmp.name)  # monkey‑patch path

# 2. Replay the corpus
num_requests = 0
with CORPUS.open() as fh:
    for row in csv.DictReader(fh, skipinitialspace=True):
        if row["policy_id"].startswith("#"):
            continue
        policy = load_policy(int(row["policy_id"]))
        ctx = RequestCtx(
            action=row["action"],
            target=row["target"],
            purpose=row["purpose"] or None,
            role=row["role"] or None,
            location=row["location"] or None,
        )
        evaluate(policy, ctx)
        num_requests += 1

# 3. Analyse the temp audit file
lines = Path(_tmp.name).read_text().splitlines()
missing: list[int] = []
for idx, ln in enumerate(lines, 1):
    try:
        rec = json.loads(ln)
        if not all(k in rec for k in ("policy_uid", "decision", "timestamp")):
            missing.append(idx)
    except json.JSONDecodeError:
        missing.append(idx)

# 4. Report
pct = (len(lines) / num_requests * 100) if num_requests else 0
coverage_ok = len(lines) == num_requests and not missing
status = "✅" if coverage_ok else "❌"
print(f"{len(lines)} lines for {num_requests} requests ({pct:.1f}%) {status}")
if not coverage_ok:
    if len(lines) != num_requests:
        print(f"  • expected {num_requests} lines but found {len(lines)}")
    if missing:
        print(f"  • {len(missing)} malformed lines: {missing[:10]} …")
else:
    sample = json.loads(lines[0])
    print("\nSample entry:")
    print(json.dumps(sample, indent=2)[:400], "…")

# Restore original audit log path (optional)
audit_log._LOG = _AUDIT_LOG_PATH
