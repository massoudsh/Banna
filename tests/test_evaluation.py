"""Regression checks for Persian scope extraction."""

from pathlib import Path

from app.evaluation import evaluate


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "evals" / "scope-regression.json"


def test_scope_regression_fixture_passes():
    results = evaluate(FIXTURE)

    assert len(results) == 3
    assert all(result.passed for result in results), results
