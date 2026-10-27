import json
from copy import deepcopy

import pytest

from eval import compare_runs


@pytest.fixture
def reports():
    a: dict = {
        "metadata": {
            "model": "fake-a",
            "sdk_version": "test",
            "questions_sha256": "hash",
            "system_instruction": "same",
            "max_steps": 5,
            "business_time": "fixed",
            "request_timeout_seconds": None,
            "total_questions": 1,
            "variant": "A",
            "commit": "source-a",
            "run_time_utc": "test-time",
            "scorer_version": 2,
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
    return {"A": a, "B": b}


def test_comparison_shows_changed_outcomes(reports):
    report = compare_runs.compare_reports(reports)
    assert "| `opening` | FAIL | PASS |" in report
    assert "100.0%" in report


@pytest.mark.parametrize("key", ["model", "system_instruction"])
def test_comparison_allows_experiments_and_displays_configuration(reports, key):
    reports["B"]["metadata"][key] = "changed"
    report = compare_runs.compare_reports(reports)
    assert "## Configuration" in report
    if key == "model":
        assert "`changed`" in report


def test_comparison_separates_scorer_versions(reports):
    reports["B"]["metadata"]["scorer_version"] = 1
    report = compare_runs.compare_reports(reports)
    assert "## 1 questions, scorer v1" in report
    assert "## 1 questions, scorer v2" in report


def test_comparison_does_not_score_incomplete_runs(reports):
    reports["B"]["results"] = []
    report = compare_runs.compare_reports(reports)
    assert "Pending/incomplete" in report
    assert "Not run" in report


def test_comparison_does_not_count_pending_review_as_pass(reports):
    reports["B"]["results"][0]["review"] = None
    report = compare_runs.compare_reports(reports)
    assert "MANUAL_REVIEW" in report
    assert "Pending/incomplete" in report


def test_comparison_rejects_duplicate_ids(reports):
    reports["B"]["results"].append(deepcopy(reports["B"]["results"][0]))
    with pytest.raises(ValueError, match="Invalid question IDs"):
        compare_runs.compare_reports(reports)


def test_comparison_rejects_changed_expectations_under_same_hash(reports):
    reports["B"]["results"][0]["case"]["expected_answer"] = "new expectation"
    with pytest.raises(ValueError, match="Different expectations"):
        compare_runs.compare_reports(reports)


def test_comparison_rejects_missing_reports():
    with pytest.raises(ValueError, match="No evaluation reports"):
        compare_runs.compare_reports({})


def test_comparison_cli_writes_report_offline(tmp_path, monkeypatch, reports):
    for name, report in reports.items():
        folder = tmp_path / name
        folder.mkdir()
        (folder / "results.json").write_text(json.dumps(report), encoding="utf-8")
    output = tmp_path / "comparison.md"
    monkeypatch.setattr(
        "sys.argv",
        ["compare_runs", "--runs-dir", str(tmp_path), "--output", str(output)],
    )
    compare_runs.main()
    assert "# Evaluation comparison" in output.read_text(encoding="utf-8")
