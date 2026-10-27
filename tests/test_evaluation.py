import json
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest

from eval import run_eval
from helpdesk.config import QUESTIONS_PATH
from helpdesk.llm import APITimeoutError, ToolTrace


@pytest.fixture
def refund_case() -> dict:
    return {
        "id": "refund_half",
        "question": "How much will I get back if I cancel CW-1002?",
        "expected_tool": "calculate_refund",
        "expected_booking_id": "CW-1002",
        "expected_amount_eur": "340.00",
        "expected_answer": "Total refund of 340 EUR.",
    }


@pytest.fixture
def refund_trace() -> list[ToolTrace]:
    return [
        {
            "step": 1,
            "call_id": "refund-call",
            "name": "calculate_refund",
            "arguments": {"booking_id": "CW-1002"},
            "result": {"refund": "340.0"},
        }
    ]


@pytest.fixture
def sample_report(refund_case, refund_trace) -> dict:
    return {
        "metadata": {
            "model": "fake-model",
            "sdk_version": "test-version",
            "variant": "test",
            "max_steps": 5,
            "run_time_utc": "2026-10-27T10:00:00+00:00",
            "business_time": "2026-06-10T09:00:00+02:00",
            "commit": "test-commit",
            "questions_sha256": "test-hash",
            "total_questions": 1,
        },
        "results": [
            {
                "case": refund_case,
                "answer": "Your refund is EUR 340.00.",
                "trace": refund_trace,
                "checks": {},
                "error": None,
                "review": None,
            }
        ],
    }


@pytest.mark.parametrize(
    "answer",
    [
        "EUR 340.00",
        "\u20ac340",
        "340 EUR",
        "340,00 euros",
        "**340.00 EUR**",
    ],
)
def test_amounts_in_recognizes_currency_formats(answer):
    assert run_eval.amounts_in(answer) == {Decimal(340)}


def test_amounts_in_does_not_confuse_other_numbers_with_expected_amount():
    assert Decimal(340) not in run_eval.amounts_in("EUR 3400; booking CW-340")


def test_check_answer_accepts_correct_refund(refund_case, refund_trace):
    checks = run_eval.check_answer(refund_case, "EUR 340.00", refund_trace)

    assert all(checks.values())


def test_check_answer_rejects_correct_amount_without_tool(refund_case):
    checks = run_eval.check_answer(refund_case, "EUR 340.00", [])

    assert checks["amount_in_answer"]
    assert not checks["expected_tool"]
    assert not checks["refund_from_tool"]


def test_check_answer_rejects_wrong_booking_id(refund_case, refund_trace):
    refund_trace[0]["arguments"]["booking_id"] = "CW-1007"

    checks = run_eval.check_answer(refund_case, "EUR 340.00", refund_trace)

    assert not checks["expected_booking_id"]
    assert not checks["refund_from_tool"]


def test_check_answer_rejects_wrong_refund_from_tool(refund_case, refund_trace):
    refund_trace[0]["result"] = {"refund": "999.00"}

    checks = run_eval.check_answer(refund_case, "EUR 340.00", refund_trace)

    assert checks["amount_in_answer"]
    assert not checks["refund_from_tool"]


def test_check_answer_rejects_wrong_amount_in_final_answer(refund_case, refund_trace):
    checks = run_eval.check_answer(refund_case, "EUR 3400.00", refund_trace)

    assert checks["refund_from_tool"]
    assert not checks["amount_in_answer"]


def test_check_answer_checks_booking_status():
    case = {
        "expected_tool": "get_booking",
        "expected_booking_id": "CW-1002",
        "expected_status": "confirmed",
    }
    trace: list[ToolTrace] = [
        {
            "step": 1,
            "call_id": "booking-call",
            "name": "get_booking",
            "arguments": {"booking_id": "CW-1002"},
            "result": {"booking": {"status": "confirmed"}},
        }
    ]

    assert all(run_eval.check_answer(case, "CW-1002 is confirmed.", trace).values())

    checks = run_eval.check_answer(case, "CW-1002 is cancelled.", trace)

    assert checks["status_from_tool"]
    assert not checks["status_in_answer"]


def test_check_answer_checks_unknown_booking():
    case = {
        "expected_tool": "get_booking",
        "expected_booking_id": "CW-9999",
        "expected_not_found": True,
    }
    trace: list[ToolTrace] = [
        {
            "step": 1,
            "call_id": "booking-call",
            "name": "get_booking",
            "arguments": {"booking_id": "CW-9999"},
            "result": {
                "booking_id": "CW-9999",
                "booking": None,
                "error": "Booking not found.",
            },
        }
    ]

    checks = run_eval.check_answer(case, "Booking CW-9999 was not found.", trace)

    assert all(checks.values())


def test_check_answer_rejects_step_limit():
    checks = run_eval.check_answer(
        {},
        "Unable to complete the request within the step limit. "
        "Please contact the staff.",
        [],
    )

    assert not checks["within_step_limit"]


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"error": "Timeout"}, "ERROR"),
        (
            {
                "checks": {"amount": False},
                "review": {"status": "PASS", "reason": "Reviewed"},
            },
            "FAIL",
        ),
        ({"checks": {"amount": True}}, "MANUAL_REVIEW"),
        ({"checks": {}}, "MANUAL_REVIEW"),
        (
            {
                "checks": {"amount": True},
                "review": {"status": "PASS", "reason": ""},
            },
            "MANUAL_REVIEW",
        ),
        (
            {
                "checks": {"amount": True},
                "review": {"status": "PASS", "reason": "Verified"},
            },
            "PASS",
        ),
        (
            {
                "checks": {"amount": True},
                "review": {"status": "FAIL", "reason": "Invented extra facts"},
            },
            "FAIL",
        ),
    ],
)
def test_final_status(entry, expected):
    assert run_eval.final_status(entry) == expected


def test_refusal_is_not_automatically_accepted():
    case = {"expected_refusal": True}
    answer = "Here is an unrelated geography answer."
    checks = run_eval.check_answer(case, answer, [])

    assert run_eval.final_status({"checks": checks}) == "MANUAL_REVIEW"


def test_write_report_saves_json_and_markdown_and_preserves_review(
    tmp_path, sample_report
):
    run_eval.write_report(sample_report, tmp_path)

    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert saved["results"][0]["checks"]["refund_from_tool"]
    assert saved["results"][0]["review"] is None
    assert "| MANUAL_REVIEW | 1 |" in (tmp_path / "results.md").read_text(
        encoding="utf-8"
    )

    sample_report["results"][0]["review"] = {
        "status": "PASS",
        "reason": "Verified amount, tool use, and wording.",
    }

    run_eval.write_report(sample_report, tmp_path)

    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert saved["results"][0]["review"]["status"] == "PASS"
    assert "| PASS | 1 |" in (tmp_path / "results.md").read_text(encoding="utf-8")


def test_report_only_does_not_require_api_key(tmp_path, sample_report, monkeypatch):
    (tmp_path / "results.json").write_text(json.dumps(sample_report), encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["run_eval", "--report-only", "--output-dir", str(tmp_path)],
    )
    fake_client = MagicMock()
    monkeypatch.setattr(run_eval.genai, "Client", fake_client)

    run_eval.main()

    fake_client.assert_not_called()
    assert (tmp_path / "results.md").exists()


@pytest.mark.parametrize("variable", ["GEMINI_API_KEY", "GEMINI_MODEL"])
def test_main_rejects_missing_configuration(variable, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")
    monkeypatch.delenv(variable)
    monkeypatch.setattr("sys.argv", ["run_eval"])
    fake_client = MagicMock()
    monkeypatch.setattr(run_eval.genai, "Client", fake_client)

    with pytest.raises(SystemExit, match=variable):
        run_eval.main()

    fake_client.assert_not_called()


def test_main_continues_after_timeout_and_saves_each_result(tmp_path, monkeypatch):
    cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")
    monkeypatch.setattr(
        "sys.argv",
        ["run_eval", "--output-dir", str(tmp_path)],
    )
    monkeypatch.setattr(
        run_eval.subprocess,
        "check_output",
        MagicMock(return_value="test-commit\n"),
    )

    client = MagicMock()
    client.__enter__.return_value = client
    fake_client = MagicMock(return_value=client)
    monkeypatch.setattr(run_eval.genai, "Client", fake_client)

    timeout = APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
    fake_agent = MagicMock(side_effect=[timeout] + ["Recovered."] * (len(cases) - 1))
    monkeypatch.setattr(run_eval, "run_agent", fake_agent)

    saved_sizes: list[int] = []
    original_write_report = run_eval.write_report

    def record_save(report, output_dir):
        saved_sizes.append(len(report["results"]))
        original_write_report(report, output_dir)

    monkeypatch.setattr(run_eval, "write_report", record_save)

    run_eval.main()

    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert len(saved["results"]) == len(cases)
    assert saved_sizes == list(range(1, len(cases) + 1))
    assert "APITimeoutError" in saved["results"][0]["error"]
    assert saved["results"][1]["answer"] == "Recovered."
    assert fake_agent.call_count == len(cases)
    fake_client.assert_called_once()
    assert all(call.kwargs["debug"] is False for call in fake_agent.call_args_list)


@pytest.mark.parametrize(
    ("answer", "expected", "matches"),
    [
        ("No further refund is available.", "0", True),
        ("No refund is due.", "0", True),
        ("Nothing will be refunded.", "0", True),
        ("You will receive no new refund.", "0", True),
        ("The refund is EUR 0.00.", "0", True),
        ("No further refund is available.", "340", False),
        ("No refund is available. You will receive EUR 50.", "0", False),
        ("The booking is cancelled.", "0", False),
        ("The booking fee has no refund, but rental is refundable.", "0", False),
    ],
)
def test_refund_amount_matches_zero_wording(answer, expected, matches):
    assert run_eval.refund_amount_matches(answer, Decimal(expected)) is matches


def test_zero_wording_still_requires_matching_refund_tool():
    case = {
        "expected_tool": "calculate_refund",
        "expected_booking_id": "CW-1005",
        "expected_amount_eur": "0",
    }

    checks = run_eval.check_answer(case, "No further refund is available.", [])

    assert checks["amount_in_answer"]
    assert not checks["refund_from_tool"]
    assert not checks["expected_tool"]


def test_report_records_scorer_version(tmp_path, sample_report):
    run_eval.write_report(sample_report, tmp_path)

    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))

    assert saved["metadata"]["scorer_version"] == 2


def test_main_selects_question_file_and_explicit_model(tmp_path, monkeypatch):
    questions_path = QUESTIONS_PATH.parent / "questions_holdout.json"
    cases = json.loads(questions_path.read_text(encoding="utf-8"))
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "environment-model")
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_eval",
            "--questions",
            str(questions_path),
            "--model",
            "selected-model",
            "--output-dir",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(
        run_eval.subprocess, "check_output", MagicMock(return_value="test-commit\n")
    )
    client = MagicMock()
    client.__enter__.return_value = client
    monkeypatch.setattr(run_eval.genai, "Client", MagicMock(return_value=client))
    fake_agent = MagicMock(return_value="Test answer.")
    monkeypatch.setattr(run_eval, "run_agent", fake_agent)
    run_eval.main()
    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert [entry["case"] for entry in saved["results"]] == cases
    assert saved["metadata"]["model"] == "selected-model"
    assert saved["metadata"]["questions_file"] == "questions_holdout.json"
    assert (
        saved["metadata"]["questions_sha256"]
        == run_eval.hashlib.sha256(questions_path.read_bytes()).hexdigest()
    )
    assert all(call.args[2] == "selected-model" for call in fake_agent.call_args_list)
