# check_corpus.py
"""
Quick correctness check for the GDPR Article-5 PDP.

Reads the public test corpus (CSV), evaluates every row with
gdpr_engine.evaluate(), and prints:
  • number of matches / accuracy %
  • 2 × 2 confusion-matrix (Permit/Deny)
  • list of mismatches (if any)

You can safely commit this file or run it ad-hoc; it has
no side-effects except reading the corpus.
"""

from __future__ import annotations

import csv
from pathlib import Path
from collections import Counter
from typing import Tuple

from gdpr_engine.evaluator import evaluate, RequestCtx
from gdpr_engine.loader import load_policy

# ── locate the corpus (same file used in the public tests) ───────────
CORPUS = Path("tests") / "corpus.csv"        # adjust if you moved it

# ── bookkeeping ───────────────────────────────────────────────────────
total   = 0
matches = 0
conf: Counter[Tuple[str, str]] = Counter()      # keys: (expected, got)

mismatches: list[str] = []

# ── main loop ─────────────────────────────────────────────────────────
with CORPUS.open() as fh:
    for row in csv.DictReader(fh, skipinitialspace=True):
        if row["policy_id"].startswith("#"):        # comment line
            continue

        policy = load_policy(int(row["policy_id"]))
        ctx = RequestCtx(
            action   = row["action"],
            target   = row["target"],
            purpose  = row["purpose"]  or None,
            role     = row["role"]     or None,
            location = row["location"] or None,
        )

        got  = evaluate(policy, ctx).value
        exp  = row["expected_decision"]

        conf[(exp, got)] += 1
        total += 1

        if got == exp:
            matches += 1
        else:
            mismatches.append(
                f"row {total:3d}: expected {exp:6s} – got {got}"
            )

# ── output ────────────────────────────────────────────────────────────
accuracy = matches / total * 100
print(f"{matches} / {total} cases matched  ({accuracy:0.1f} % accuracy)")

# small confusion matrix
tp = conf[("Permit", "Permit")]
tn = conf[("Deny",   "Deny")]
fp = conf[("Deny",   "Permit")]
fn = conf[("Permit", "Deny")]

print("\nConfusion matrix (rows = expected, cols = got)")
print("            Permit   Deny")
print(f"Permit   |  {tp:5d}   {fn:5d}")
print(f"Deny     |  {fp:5d}   {tn:5d}\n")

if mismatches:
    print("Mismatches:")
    print("\n".join(mismatches))
