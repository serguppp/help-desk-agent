import json
from unittest.mock import MagicMock

from google import genai
from google.genai.interactions import (
    FunctionCallStep,
    Interaction,
    ModelOutputStep,
    TextContent,
)

from helpdesk import llm


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

    client = MagicMock(spec=genai.Client)
    client.interactions.create.side_effect = [
        Interaction(
            id="interaction-1",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id="call-1",
                    name="search_policies",
                    arguments={"query": "dog"},
                )
            ],
        ),
        Interaction(
            id="interaction-2",
            status="completed",
            steps=[ModelOutputStep(content=[TextContent(text=sections[0]["text"])])],
        ),
    ]

    answer = llm.run_agent("Can I take my dog?", client, "fake-model")

    assert answer == sections[0]["text"]
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

    client = MagicMock(spec=genai.Client)
    client.interactions.create.side_effect = [
        Interaction(
            id=f"interaction-{index}",
            status="requires_action",
            steps=[
                FunctionCallStep(
                    id=f"call-{index}",
                    name="search_policies",
                    arguments={"query": "unknown"},
                )
            ],
        )
        for index in range(3)
    ]

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
