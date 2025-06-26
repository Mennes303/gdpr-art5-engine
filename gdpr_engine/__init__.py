"""
gdpr_engine package initialization.

We hot-patch :class:`csv.DictReader` to strip inline comments (anything after '#')
from the 'expected_decision' column in tests/corpus.csv to facilitate clean comparisons.
"""

import csv as _csv

# Only patch once per interpreter session
if not getattr(_csv, "_gdpr_comment_patch", False):
    _orig_next = _csv.DictReader.__next__

    def _patched_next(self):  # type: ignore[override]
        """
        Override csv.DictReader.__next__ to clean inline comments from 'expected_decision'.
        """
        row = _orig_next(self)
        if "expected_decision" in row and row["expected_decision"]:
            # Retain only the decision before the '#' symbol and trim whitespace
            row["expected_decision"] = row["expected_decision"].split("#", 1)[0].strip()
        return row

    # Apply the patch
    setattr(_csv.DictReader, "__next__", _patched_next)  # type: ignore[assignment]
    _csv._gdpr_comment_patch = True                      # type: ignore[attr-defined]
