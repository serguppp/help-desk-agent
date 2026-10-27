from decimal import InvalidOperation
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai._gaos.lib.compat_errors import InternalServerError

from helpdesk import llm

REQUEST = httpx.Request("POST", "https://example.invalid")


@pytest.fixture
def fake_cli_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")

    client = MagicMock()
    client.__enter__.return_value = client
    monkeypatch.setattr(
        llm.genai,
        "Client",
        MagicMock(return_value=client),
    )
    return client


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (
            llm.APITimeoutError(request=REQUEST),
            "The request timed out",
        ),
        (
            InternalServerError(
                "Service unavailable",
                response=httpx.Response(503, request=REQUEST),
                body=None,
            ),
            "The AI service request failed",
        ),
        (FileNotFoundError("missing file"), "CityWheels data could not be read"),
        (ValueError("invalid date"), "CityWheels data could not be read"),
        (KeyError("start"), "CityWheels data could not be read"),
        (InvalidOperation(), "CityWheels data could not be read"),
        (RuntimeError("empty response"), "The assistant could not complete"),
    ],
)
def test_cli_continues_after_error(
    error, expected_message, fake_cli_client, monkeypatch, capsys
):
    monkeypatch.setattr(
        "builtins.input",
        MagicMock(side_effect=["first question", "second question", "exit"]),
    )
    fake_agent = MagicMock(side_effect=[error, "Recovered"])
    monkeypatch.setattr(llm, "run_agent", fake_agent)

    llm.main()

    output = capsys.readouterr().out
    assert expected_message in output
    assert "Agent: Recovered" in output
    assert [call.args[0] for call in fake_agent.call_args_list] == [
        "first question",
        "second question",
    ]
    fake_cli_client.__exit__.assert_called_once()


@pytest.mark.parametrize("command", ["exit", "quit"])
def test_cli_skips_empty_input_and_exits(command, fake_cli_client, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        MagicMock(side_effect=["", "   ", command]),
    )
    fake_agent = MagicMock()
    monkeypatch.setattr(llm, "run_agent", fake_agent)

    llm.main()

    fake_agent.assert_not_called()
    fake_cli_client.__exit__.assert_called_once()


@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_cli_handles_interrupted_input(
    interruption, fake_cli_client, monkeypatch, capsys
):
    monkeypatch.setattr(
        "builtins.input",
        MagicMock(side_effect=interruption),
    )
    fake_agent = MagicMock()
    monkeypatch.setattr(llm, "run_agent", fake_agent)

    llm.main()

    assert "Goodbye." in capsys.readouterr().out
    fake_agent.assert_not_called()
    fake_cli_client.__exit__.assert_called_once()


@pytest.mark.parametrize("variable", ["GEMINI_API_KEY", "GEMINI_MODEL"])
def test_cli_reports_missing_configuration(variable, fake_cli_client, monkeypatch):
    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(SystemExit, match=variable):
        llm.main()

    fake_cli_client.__enter__.assert_not_called()
