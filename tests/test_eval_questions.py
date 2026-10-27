import json
from decimal import Decimal

import pytest

from helpdesk.config import QUESTIONS_PATH


@pytest.fixture
def evaluation_questions() -> list[dict]:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    assert isinstance(questions, list)
    return questions


def test_evaluation_questions_have_valid_fields_and_unique_ids(
    evaluation_questions,
):
    ids: list[str] = []
    allowed_tools = {"search_policies", "get_booking", "calculate_refund"}

    for case in evaluation_questions:
        assert isinstance(case, dict)

        for field in ("id", "question", "expected_answer"):
            assert isinstance(case.get(field), str)
            assert case[field].strip(), f"Empty field: {field}"

        ids.append(case["id"])

        if "expected_tool" in case:
            assert case["expected_tool"] in allowed_tools

    assert len(ids) == len(set(ids)), "Evaluation IDs must be unique"


def test_evaluation_questions_meet_assignment_minimums(evaluation_questions):
    refund_cases = [
        case
        for case in evaluation_questions
        if case.get("expected_tool") == "calculate_refund"
        and "expected_amount_eur" in case
    ]
    refusal_cases = [
        case for case in evaluation_questions if case.get("expected_refusal") is True
    ]

    assert len(evaluation_questions) >= 10
    assert len(refund_cases) >= 2
    assert len(refusal_cases) >= 2


def test_expected_refund_amounts_are_valid(evaluation_questions):
    for case in evaluation_questions:
        if "expected_amount_eur" not in case:
            continue

        assert isinstance(case["expected_amount_eur"], str)

        amount = Decimal(case["expected_amount_eur"])

        assert amount.is_finite()
        assert amount >= 0
