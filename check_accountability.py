# check_accountability.py
"""
Accountability check for the GDPR-Article-5 PDP.

• Feeds the full test-corpus (CSV) through evaluate()
• Redirects gdpr_engine.audit_log to a temporary file
• Verifies:
    – number of JSONL lines == number of requests
    – every line contains 'policy_uid', 'decision', 'timestamp'
• Prints a one-line coverage statement and shows a sample entry
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from gdpr_engine.audit_log import _LOG as _AUDIT_LOG_PATH  # original path
from gdpr_engine import audit_log                          # the module
from gdpr_engine.evaluator import RequestCtx, evaluate
from gdpr_engine.loader import load_policy

CORPUS = Path("tests") / "corpus.csv"          # adjust if you moved it

# ── 1) redirect audit-log to a fresh temp file ───────────────────────
tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
audit_log._LOG = Path(tmp_file.name)           # monkey-patch

# ── 2) replay the whole corpus ───────────────────────────────────────
num_requests = 0
with CORPUS.open() as fh:
    for row in csv.DictReader(fh, skipinitialspace=True):
        if row["policy_id"].startswith("#"):
            continue
        policy = load_policy(int(row["policy_id"]))
        ctx = RequestCtx(
            action   = row["action"],
            target   = row["target"],
            purpose  = row["purpose"]  or None,
            role     = row["role"]     or None,
            location = row["location"] or None,
        )
        evaluate(policy, ctx)
        num_requests += 1

# ── 3) analyse the temp audit file ───────────────────────────────────
audit_path = Path(tmp_file.name)
lines = audit_path.read_text().splitlines()
num_lines = len(lines)

missing = []           # collect indices of bad entries
for idx, ln in enumerate(lines, 1):
    try:
        rec = json.loads(ln)
        if not all(k in rec for k in ("policy_uid", "decision", "timestamp")):
            missing.append(idx)
    except json.JSONDecodeError:
        missing.append(idx)

# ── 4) report ────────────────────────────────────────────────────────
coverage_ok = num_lines == num_requests and not missing
pct = (num_lines / num_requests * 100) if num_requests else 0

print(f"{num_lines} lines written for {num_requests} requests "
      f"({pct:.1f} % coverage) {'✅' if coverage_ok else '❌'}")

if not coverage_ok:
    if num_lines != num_requests:
        print(f"  • expected {num_requests} lines but found {num_lines}")
    if missing:
        print(f"  • {len(missing)} malformed JSON lines: {missing[:10]} ...")
else:
    sample = json.loads(lines[0])
    print("\nSample entry:")
    print(json.dumps(sample, indent=2)[:400], "…")

# optional: restore original log path
audit_log._LOG = _AUDIT_LOG_PATH
