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
    assert fake_search.call_count == 2
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


def test_dispatcher_does_not_hide_invalid_booking_json(monkeypatch):
    def broken_booking(_booking_id):
        raise json.JSONDecodeError("Invalid JSON", "", 0)

    monkeypatch.setattr(llm, "get_booking", broken_booking)

    with pytest.raises(json.JSONDecodeError):
        llm.execute_tool("get_booking", {"booking_id": "CW-1002"})


def test_agent_returns_final_text_without_executing_tools(monkeypatch, capsys):
    client = make_fake_client(
        "search_policies",
        {"query": "unused"},
        tool_calls=0,
        answer="Please contact the staff.",
    )
    fake_dispatcher = MagicMock()
    monkeypatch.setattr(llm, "execute_tool", fake_dispatcher)

    answer = llm.run_agent(
        "An unsupported question",
        client,
        "fake-model",
        max_steps=1,
    )

    assert answer == "Please contact the staff."
    assert client.interactions.create.call_count == 1
    fake_dispatcher.assert_not_called()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("tool_name", ["get_booking", "calculate_refund"])
def test_agent_sends_unknown_booking_result_to_model(tool_name, capsys):
    client = make_fake_client(
        tool_name,
        {"booking_id": "CW-9999"},
        answer="Booking CW-9999 was not found.",
    )

    answer = llm.run_agent("Find booking CW-9999.", client, "fake-model")

    assert answer == "Booking CW-9999 was not found."
    assert client.interactions.create.call_count == 2
    assert capsys.readouterr().out == ""

    request = client.interactions.create.call_args_list[1].kwargs
    assert request["previous_interaction_id"] == "interaction-1"

    tool_result = request["input"][0]
    assert tool_result["name"] == tool_name
    assert tool_result["call_id"] == "call-1"
    assert json.loads(tool_result["result"][0]["text"]) == {
        "booking_id": "CW-9999",
        "booking": None,
        "error": "Booking not found.",
    }


def test_agent_sends_all_tool_results_from_one_model_response():
    client = MagicMock(spec=genai.Client)
    client.interactions.create.side_effect = [
        Interaction(
            id="interaction-1",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id="booking-call",
                    name="get_booking",
                    arguments={"booking_id": "CW-1002"},
                ),
                FunctionCallStep(
                    id="refund-call",
                    name="calculate_refund",
                    arguments={"booking_id": "CW-1002"},
                ),
            ],
        ),
        Interaction(
            id="interaction-2",
            status="completed",
            steps=[
                ModelOutputStep(content=[TextContent(text="The refund is EUR 340.")])
            ],
        ),
    ]

    trace: list[llm.ToolTrace] = []
    answer = llm.run_agent(
        "Check CW-1002 and its refund.",
        client,
        "fake-model",
        trace=trace,
    )

    assert answer == "The refund is EUR 340."
    assert client.interactions.create.call_count == 2

    request = client.interactions.create.call_args_list[1].kwargs
    assert request["previous_interaction_id"] == "interaction-1"

    results = request["input"]
    assert len(results) == 2
    assert [result["type"] for result in results] == [
        "function_result",
        "function_result",
    ]
    assert [result["call_id"] for result in results] == [
        "booking-call",
        "refund-call",
    ]
    assert [result["name"] for result in results] == [
        "get_booking",
        "calculate_refund",
    ]

    booking_payload = json.loads(results[0]["result"][0]["text"])
    refund_payload = json.loads(results[1]["result"][0]["text"])

    assert booking_payload["booking"]["id"] == "CW-1002"
    assert booking_payload["error"] is None
    assert refund_payload["booking"]["id"] == "CW-1002"
    assert Decimal(refund_payload["refund"]) == Decimal(340)

    assert [call["call_id"] for call in trace] == [
        "booking-call",
        "refund-call",
    ]
    assert [call["step"] for call in trace] == [1, 1]


def test_agent_rejects_response_without_text_or_tool_calls():
    client = MagicMock(spec=genai.Client)
    client.interactions.create.return_value = Interaction(
        id="interaction-1",
        status="completed",
        steps=[],
    )

    with pytest.raises(RuntimeError, match="neither text nor tool calls"):
        llm.run_agent("Test question", client, "fake-model")

    assert client.interactions.create.call_count == 1


@pytest.mark.parametrize("question", ["", "   \t\n"])
def test_agent_rejects_empty_question_before_calling_model(question):
    client = make_fake_client(
        "search_policies",
        {"query": "unused"},
        tool_calls=0,
    )

    with pytest.raises(ValueError, match="Question must not be empty"):
        llm.run_agent(question, client, "fake-model")

    client.interactions.create.assert_not_called()


@pytest.mark.parametrize("max_steps", [0, -1])
def test_agent_rejects_invalid_step_limit_before_calling_model(max_steps):
    client = make_fake_client(
        "search_policies",
        {"query": "unused"},
        tool_calls=0,
    )

    with pytest.raises(ValueError, match="max_steps must be positive"):
        llm.run_agent(
            "Test question",
            client,
            "fake-model",
            max_steps=max_steps,
        )

    client.interactions.create.assert_not_called()


def test_agent_does_not_execute_tools_without_budget_for_their_results(
    monkeypatch, capsys
):
    client = make_fake_client(
        "search_policies",
        {"query": "open"},
        tool_calls=1,
        answer=None,
    )
    fake_dispatcher = MagicMock()
    monkeypatch.setattr(llm, "execute_tool", fake_dispatcher)
    trace: list[llm.ToolTrace] = []

    answer = llm.run_agent(
        "When are you open?",
        client,
        "fake-model",
        max_steps=1,
        trace=trace,
    )

    assert "step limit" in answer
    assert "contact the staff" in answer
    assert client.interactions.create.call_count == 1
    fake_dispatcher.assert_not_called()
    assert trace == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("booking_id", ["CW-1005", "CW-1006", "CW-1008"])
def test_agent_sends_zero_refund_and_cancellation_reason(booking_id):
    client = make_fake_client("calculate_refund", {"booking_id": booking_id})

    llm.run_agent(f"Can I cancel {booking_id}?", client, "fake-model")

    request = client.interactions.create.call_args_list[1].kwargs
    payload = json.loads(request["input"][0]["result"][0]["text"])

    assert Decimal(payload["refund"]) == 0
    assert payload["booking"]["id"] == booking_id
    assert payload["booking"]["status"] in payload["message"]


def test_agent_sends_refund_breakdown_and_methods_to_model():
    client = make_fake_client("calculate_refund", {"booking_id": "CW-1004"})

    llm.run_agent("What is the refund for CW-1004?", client, "fake-model")

    request = client.interactions.create.call_args_list[1].kwargs
    payload = json.loads(request["input"][0]["result"][0]["text"])

    assert payload["cancellation_allowed"] is True
    assert Decimal(payload["rental_refund_eur"]) == Decimal(23)
    assert Decimal(payload["deposit_refund_eur"]) == Decimal(50)
    assert Decimal(payload["booking_fee_refund_eur"]) == 0
    assert Decimal(payload["refund"]) == Decimal(73)
    assert payload["rental_refund_method"] == "New voucher, never money."
    assert payload["deposit_refund_method"] == "Original deposit payment method."


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"file_name": ".env"},
        {"file_name": "../faq.md"},
        {"file_name": 123},
        {"file_name": "faq.md", "extra": True},
    ],
)
def test_agent_sends_document_argument_errors_back_to_model(arguments):
    client = make_fake_client("read_policy_document", arguments)

    llm.run_agent("Read a document", client, "fake-model")

    request = client.interactions.create.call_args_list[1].kwargs
    payload = json.loads(request["input"][0]["result"][0]["text"])

    assert payload.get("error")


def test_agent_can_read_document_after_empty_search(monkeypatch, tmp_path):
    from helpdesk import policies

    text = "# FAQ\n## Where are you?\nAt the Riverside Park entrance.\n"
    (tmp_path / "faq.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(policies, "POLICIES_PATH", tmp_path)
    monkeypatch.setattr(llm, "search_policies", lambda _: [])

    client = MagicMock(spec=genai.Client)
    client.interactions.create.side_effect = [
        Interaction(
            id="search-interaction",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id="search-call",
                    name="search_policies",
                    arguments={"query": "location"},
                )
            ],
        ),
        Interaction(
            id="document-interaction",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id="document-call",
                    name="read_policy_document",
                    arguments={"file_name": "faq.md"},
                )
            ],
        ),
        Interaction(
            id="final-interaction",
            status="completed",
            steps=[
                ModelOutputStep(
                    content=[TextContent(text="At the Riverside Park entrance.")]
                )
            ],
        ),
    ]

    trace: list[llm.ToolTrace] = []
    answer = llm.run_agent(
        "Where are you?",
        client,
        "fake-model",
        trace=trace,
    )

    assert answer == "At the Riverside Park entrance."
    assert client.interactions.create.call_count == 3

    search_result_request = client.interactions.create.call_args_list[1].kwargs
    assert search_result_request["previous_interaction_id"] == "search-interaction"
    assert json.loads(search_result_request["input"][0]["result"][0]["text"]) == []

    document_result_request = client.interactions.create.call_args_list[2].kwargs
    assert document_result_request["previous_interaction_id"] == "document-interaction"

    result = document_result_request["input"][0]
    assert result["name"] == "read_policy_document"
    assert result["call_id"] == "document-call"
    assert json.loads(result["result"][0]["text"]) == {
        "source": "faq.md",
        "text": text,
    }
    assert [call["name"] for call in trace] == [
        "search_policies",
        "read_policy_document",
    ]


@pytest.mark.parametrize("timeout", [None, 10.5])
def test_shared_client_uses_consistent_timeout_units(timeout, monkeypatch):
    monkeypatch.setattr(llm, "REQUEST_TIMEOUT_SECONDS", timeout)
    factory = MagicMock()
    monkeypatch.setattr(llm.genai, "Client", factory)
    llm.create_client("fake-key")
    options = factory.call_args.kwargs["http_options"]
    assert options.timeout == (10500 if timeout is not None else None)
    assert options.client_args["timeout"] == timeout
