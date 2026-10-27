from copy import deepcopy

import pytest

from eval.compare_runs import compare_reports


@pytest.fixture
def reports():
    a: dict = {
        "metadata": {
            "model": "fake",
            "sdk_version": "test",
            "questions_sha256": "hash",
            "system_instruction": "same",
            "max_steps": 5,
            "business_time": "fixed",
            "request_timeout_seconds": None,
            "total_questions": 1,
            "variant": "A",
            "commit": "source-a",
        },
        "results": [
            {
                "case": {"id": "opening", "question": "Open?"},
                "trace": [],
                "checks": {"nonempty_answer": True},
                "error": None,
                "review": {"status": "FAIL", "reason": "Wrong answer"},
            }
        ],
    }
    b = deepcopy(a)
    b["metadata"].update(variant="B", commit="source-b")
    b["results"][0]["review"] = {"status": "PASS", "reason": "Correct answer"}
    return a, b


def test_comparison_shows_changed_outcomes(reports):
    report = compare_reports(*reports)
    assert "| opening | FAIL | PASS |" in report
    assert "| PASS | 0 | 1 |" in report


@pytest.mark.parametrize(
    "key", ["model", "system_instruction", "questions_sha256", "scorer_version"]
)
def test_comparison_rejects_different_configuration(reports, key):
    a, b = reports
    b["metadata"][key] = "changed"
    with pytest.raises(ValueError):
        compare_reports(a, b)


def test_comparison_rejects_incomplete_run(reports):
    a, b = reports
    b["results"] = []
    with pytest.raises(ValueError, match="Incomplete"):
        compare_reports(a, b)


def test_comparison_rejects_changed_expectations(reports):
    a, b = reports
    b["results"][0]["case"]["expected_answer"] = "new expectation"
    with pytest.raises(ValueError, match="Different questions"):
        compare_reports(a, b)
