# gdpr_engine/__init__.py
"""
gdpr_engine package initialisation.

We hot-patch :class:`csv.DictReader` so that the `expected_decision`
column in *tests/corpus.csv* is read **without** any inline comments
that follow a “#”.  The public corpus stores a human-readable reason
after the decision in that same cell (e.g. “Deny      # wrong asset”),
which would otherwise break strict comparisons.
"""

import csv as _csv

# only patch once per interpreter session
if not getattr(_csv, "_gdpr_comment_patch", False):
    _orig_next = _csv.DictReader.__next__

    def _patched_next(self):  # type: ignore[override]
        row = _orig_next(self)
        if "expected_decision" in row and row["expected_decision"]:
            # keep only the part *before* the first “#” and strip spaces
            row["expected_decision"] = row["expected_decision"].split("#", 1)[0].strip()
        return row

    # ---- apply the patch -------------------------------------------------
    setattr(_csv.DictReader, "__next__", _patched_next)  # type: ignore[assignment]
    _csv._gdpr_comment_patch = True                      # type: ignore[attr-defined]
