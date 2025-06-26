"""
Ad‑hoc correctness checker for the GDPR Article‑5 PDP.

* Replays every row in *tests/corpus.csv* through ``evaluate``.
* Prints accuracy, a tiny 2×2 confusion matrix, and any mismatches.

Read‑only: no side‑effects besides console output.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Tuple

from gdpr_engine.evaluator import evaluate, RequestCtx
from gdpr_engine.loader import load_policy

CORPUS = Path("tests") / "corpus.csv"  # adjust if moved

# Counters
matches = 0
conf: Counter[Tuple[str, str]] = Counter()
rows_seen: list[str] = []

with CORPUS.open() as fh:
    for idx, row in enumerate(csv.DictReader(fh, skipinitialspace=True), 1):
        if row["policy_id"].startswith("#"):
            continue  # skip comments

        policy = load_policy(int(row["policy_id"]))
        ctx = RequestCtx(
            action=row["action"],
            target=row["target"],
            purpose=row["purpose"] or None,
            role=row["role"] or None,
            location=row["location"] or None,
        )
        got = evaluate(policy, ctx).value
        exp = row["expected_decision"]
        conf[(exp, got)] += 1
        if got != exp:
            rows_seen.append(f"row {idx:3d}: expected {exp:<6} – got {got}")
        else:
            matches += 1

total = matches + len(rows_seen)
acc = matches / total * 100 if total else 0
print(f"{matches} / {total} cases matched  ({acc:.1f}% accuracy)")

tp = conf[("Permit", "Permit")]
fn = conf[("Permit", "Deny")]
fp = conf[("Deny", "Permit")]
tn = conf[("Deny", "Deny")]
print("\nConfusion matrix (expected ↘ vs got →)")
print("            Permit   Deny")
print(f"Permit   |  {tp:5d}   {fn:5d}")
print(f"Deny     |  {fp:5d}   {tn:5d}\n")

if rows_seen:
    print("Mismatches:")
    print("\n".join(rows_seen))
