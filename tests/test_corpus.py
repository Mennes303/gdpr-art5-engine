import csv
import pathlib
import pytest

from gdpr_engine.evaluator import evaluate, RequestCtx
from gdpr_engine.loader import load_policy

CORPUS = pathlib.Path(__file__).parent / "corpus.csv"

@pytest.mark.parametrize(
    "row",
    csv.DictReader(CORPUS.open(), skipinitialspace=True),
)
def test_corpus_row(row):
    # skip comment lines that start with '#'
    if row["policy_id"].startswith("#"):
        return

    policy = load_policy(int(row["policy_id"]))
    ctx = RequestCtx(
        action=row["action"],
        target=row["target"],
        purpose=row["purpose"] or None,
        role=row["role"] or None,
        location=row["location"] or None,
    )
    assert evaluate(policy, ctx).value == row["expected_decision"]
