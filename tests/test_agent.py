import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from google import genai
from google.genai.interactions import (
    FunctionCallStep,
    Interaction,
    ModelOutputStep,
    TextContent,
)

from helpdesk import llm


def make_fake_client(
    tool_name: str,
    arguments: dict[str, object],
    *,
    tool_calls: int = 1,
    answer: str | None = "Test answer.",
) -> MagicMock:
    responses = [
        Interaction(
            id=f"interaction-{index}",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id=f"call-{index}",
                    name=tool_name,
                    arguments=arguments,
                )
            ],
        )
        for index in range(1, tool_calls + 1)
    ]

    if answer is not None:
        responses.append(
            Interaction(
                id="final-interaction",
                status="completed",
                steps=[ModelOutputStep(content=[TextContent(text=answer)])],
            )
        )

    client = MagicMock(spec=genai.Client)
    client.interactions.create.side_effect = responses
    return client


def test_agent_executes_tool_and_sends_result_to_model(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    sections = [
        {
            "source": "faq.md",
            "heading": "Can I take my dog?",
            "text": "Dogs are not allowed in bike baskets or child seats.",
        }
    ]
    fake_search = MagicMock(return_value=sections)
    monkeypatch.setattr(llm, "search_policies", fake_search)
    client = make_fake_client("search_policies", {"query": "dog"})

    answer = llm.run_agent("Can I take my dog?", client, "fake-model")

    assert answer == "Test answer."
    fake_search.assert_called_once_with("dog")
    assert client.interactions.create.call_count == 2

    first_request = client.interactions.create.call_args_list[0].kwargs
    assert first_request["input"] == "Can I take my dog?"

    second_request = client.interactions.create.call_args_list[1].kwargs
    assert second_request["previous_interaction_id"] == "interaction-1"
    assert second_request["tools"] == llm.TOOLS
    assert second_request["system_instruction"] == llm.SYSTEM_INSTRUCTION

    tool_result = second_request["input"][0]
    assert tool_result["type"] == "function_result"
    assert tool_result["name"] == "search_policies"
    assert tool_result["call_id"] == "call-1"
    assert json.loads(tool_result["result"][0]["text"]) == sections


def test_agent_stops_at_step_limit(monkeypatch):
    fake_search = MagicMock(return_value=[])
    monkeypatch.setattr(llm, "search_policies", fake_search)
    client = make_fake_client(
        "search_policies",
        {"query": "unknown"},
        tool_calls=3,
        answer=None,
    )

    answer = llm.run_agent(
        "Find something",
        client,
        "fake-model",
        max_steps=3,
    )

    assert client.interactions.create.call_count == 3
    assert fake_search.call_count == 3
    assert "step limit" in answer
    assert "contact the staff" in answer


def test_agent_exposes_all_required_tools():
    names = [tool.get("name") for tool in llm.TOOLS]

    assert "search_policies" in names
    assert "get_booking" in names
    assert "calculate_refund" in names


@pytest.mark.parametrize("tool_name", ["get_booking", "calculate_refund"])
def test_agent_sends_booking_and_refund_as_json(tool_name):
    client = make_fake_client(tool_name, {"booking_id": "CW-1002"})

    trace: list[llm.ToolTrace] = []
    answer = llm.run_agent(
        "Question about CW-1002",
        client,
        "fake-model",
        trace=trace,
    )

    assert answer == "Test answer."
    assert client.interactions.create.call_count == 2

    request = client.interactions.create.call_args_list[1].kwargs
    assert request["previous_interaction_id"] == "interaction-1"

    tool_result = request["input"][0]
    assert tool_result["type"] == "function_result"
    assert tool_result["name"] == tool_name
    assert tool_result["call_id"] == "call-1"

    payload = json.loads(tool_result["result"][0]["text"])

    assert len(trace) == 1
    assert trace[0]["step"] == 1
    assert trace[0]["name"] == tool_name
    assert trace[0]["call_id"] == "call-1"
    assert trace[0]["arguments"] == {"booking_id": "CW-1002"}
    assert trace[0]["result"] == payload
    json.dumps(trace)

    booking = payload["booking"]
    assert booking["id"] == "CW-1002"
    assert booking["status"] == "confirmed"
    assert booking["start"] == "2026-06-11T18:00:00+02:00"
    assert booking["end"] == "2026-06-12T18:00:00+02:00"

    for field in ("rental_price_eur", "booking_fee_eur", "deposit_eur"):
        assert isinstance(booking[field], str)

    assert Decimal(booking["rental_price_eur"]) == Decimal(80)
    assert Decimal(booking["booking_fee_eur"]) == Decimal(2)
    assert Decimal(booking["deposit_eur"]) == Decimal(300)

    if tool_name == "calculate_refund":
        assert isinstance(payload["refund"], str)
        assert Decimal(payload["refund"]) == Decimal(340)
    else:
        assert payload["error"] is None


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("unknown_tool", {}),
        ("get_booking", {}),
        ("get_booking", {"booking_id": 123}),
        ("get_booking", {"booking_id": "CW-1002", "extra": "value"}),
        ("calculate_refund", {"booking_id": ""}),
        ("calculate_refund", {"booking_id": None}),
        ("search_policies", {"query": 123}),
        ("search_policies", {"query": "   "}),
        ("search_policies", {"booking_id": "CW-1002"}),
    ],
)
def test_agent_sends_tool_errors_back_to_model(tool_name, arguments):
    client = make_fake_client(tool_name, arguments)

    answer = llm.run_agent("Test question", client, "fake-model")

    assert answer == "Test answer."
    assert client.interactions.create.call_count == 2

    request = client.interactions.create.call_args_list[1].kwargs
    tool_result = request["input"][0]

    assert tool_result["name"] == tool_name
    assert tool_result["call_id"] == "call-1"

    payload = json.loads(tool_result["result"][0]["text"])
    assert isinstance(payload, dict)
    assert payload.get("error")


def test_serialization_rejects_unsupported_type():
    with pytest.raises(TypeError, match="Cannot serialize"):
        json.dumps(object(), default=llm.serialize_tool_value)
