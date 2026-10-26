import json
import os

from google import genai
from google.genai.interactions import (
    FunctionResultStepParam,
    Interaction,
    ToolParam,
)

from .policies import PolicySections, search_policies

TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "search_policies",
        "description": (
            "Search CityWheels policies using a short English keyword or phrase. Correct obvious spelling mistakes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A short English search phrase, for example: dog, open, booking fee."
                    ),
                },
            },
            "required": ["query"],
        },
    },
]

SYSTEM_INSTRUCTION = (
    "You are the CityWheels help desk assistant. "
    "Use search_policies before answering policy questions. "
    "Answer only using information retrieved from the policies. "
    "Never invent facts or prices. "
    "If a search does not provide enough information, "
    "you may try another short English search phrase. "
    "If information is unavailable or the question is unrelated "
    "to CityWheels, say so and direct the customer to the staff."
)


def execute_tool(
    name: str,
    arguments: dict[str, object],
) -> list[PolicySections] | dict[str, str]:
    if name != "search_policies":
        return {"error": "unknown_tool"}

    query = arguments.get("query")

    if set(arguments) != {"query"} or not isinstance(query, str):
        return {"error": "Expected one string argument: query"}

    try:
        return search_policies(query)
    except ValueError as error:
        return {"error": str(error)}


def run_agent(
    question: str,
    client: genai.Client,
    model: str,
    max_steps: int = 5,
) -> str:
    if not question.strip():
        raise ValueError("Question must not be empty")

    if max_steps < 1:
        raise ValueError("max_steps must be positive")

    interaction = client.interactions.create(
        model=model,
        input=question,
        tools=TOOLS,
        system_instruction=SYSTEM_INSTRUCTION,
        stream=False,
        timeout=30.0,
    )

    for step_index in range(max_steps):
        if not isinstance(interaction, Interaction):
            raise TypeError("Expected a non-streaming response")

        tool_results: list[FunctionResultStepParam] = []

        for step in interaction.steps or []:
            if step.type != "function_call":
                continue

            print("Executing tool:", step.name)
            print("Arguments:", step.arguments)

            result = execute_tool(step.name, step.arguments)

            tool_results.append(
                {
                    "type": "function_result",
                    "name": step.name,
                    "call_id": step.id,
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False),
                        }
                    ],
                }
            )

        if not tool_results:
            if not interaction.output_text:
                raise RuntimeError("The model returned neither text nor tool calls")

            return interaction.output_text

        if step_index == max_steps - 1:
            break

        if not interaction.id:
            raise RuntimeError("Missing interaction ID")

        interaction = client.interactions.create(
            model=model,
            previous_interaction_id=interaction.id,
            input=tool_results,
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
            stream=False,
            timeout=30.0,
        )

    return (
        "Unable to complete the request within the step limit. "
        "Please contact the staff."
    )


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    if not model:
        raise ValueError("GEMINI_MODEL is not configured")

    question = input("You: ").strip()

    with genai.Client(api_key=api_key) as client:
        answer = run_agent(question, client, model)

    print("Agent:", answer)


if __name__ == "__main__":
    main()
