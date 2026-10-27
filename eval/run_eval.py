import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter

from google import genai
from google.genai import types

from helpdesk.config import PROJECT_ROOT, QUESTIONS_PATH, TIME_NOW
from helpdesk.llm import (
    SYSTEM_INSTRUCTION,
    InteractionsAPIError,
    ToolTrace,
    run_agent,
)

MAX_STEPS = 5

MONEY = re.compile(
    r"(?:EUR\b|\u20ac)\s*(-?\d+(?:[.,]\d+)?)"
    r"|(-?\d+(?:[.,]\d+)?)\s*(?:EUR\b|euros?\b|\u20ac)",
    re.IGNORECASE,
)


def amounts_in(answer: str) -> set[Decimal]:
    return {
        Decimal((match.group(1) or match.group(2)).replace(",", "."))
        for match in MONEY.finditer(answer.replace("*", ""))
    }


def check_answer(
    case: dict,
    answer: str,
    trace: list[ToolTrace],
) -> dict[str, bool]:
    checks = {
        "nonempty_answer": bool(answer.strip()),
        "within_step_limit": not answer.startswith(
            "Unable to complete the request within the step limit."
        ),
    }

    calls = trace

    if "expected_tool" in case:
        calls = [call for call in calls if call["name"] == case["expected_tool"]]
        checks["expected_tool"] = bool(calls)

    if "expected_booking_id" in case:
        calls = [
            call
            for call in calls
            if call["arguments"].get("booking_id") == case["expected_booking_id"]
        ]
        checks["expected_booking_id"] = bool(calls)

    payloads = [call["result"] for call in calls if isinstance(call["result"], dict)]

    if "expected_amount_eur" in case:
        expected = Decimal(case["expected_amount_eur"])

        checks["refund_from_tool"] = any(
            "refund" in payload and Decimal(str(payload["refund"])) == expected
            for payload in payloads
        )
        checks["amount_in_answer"] = expected in amounts_in(answer)

    if "expected_status" in case:
        status = case["expected_status"]

        checks["status_from_tool"] = any(
            isinstance(payload.get("booking"), dict)
            and payload["booking"].get("status") == status
            for payload in payloads
        )
        checks["status_in_answer"] = bool(
            re.search(rf"\b{re.escape(status)}\b", answer, re.IGNORECASE)
        )

    if case.get("expected_not_found"):
        checks["not_found_from_tool"] = any(
            "booking" in payload
            and payload["booking"] is None
            and bool(payload.get("error"))
            for payload in payloads
        )
        checks["not_found_in_answer"] = bool(
            re.search(
                r"\b(not found|could not find|cannot find|does not exist)\b",
                answer,
                re.IGNORECASE,
            )
        )

    return checks


def final_status(entry: dict) -> str:
    if entry.get("error"):
        return "ERROR"

    if not entry.get("checks"):
        return "MANUAL_REVIEW"

    if not all(entry["checks"].values()):
        return "FAIL"

    review = entry.get("review") or {}

    if review.get("status") in {"PASS", "FAIL"} and review.get("reason", "").strip():
        return review["status"]

    return "MANUAL_REVIEW"


def write_report(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for entry in report["results"]:
        if not entry.get("error"):
            entry["checks"] = check_answer(
                entry["case"],
                entry["answer"],
                entry["trace"],
            )

    counts = Counter(final_status(entry) for entry in report["results"])

    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata = report["metadata"]
    lines = [
        "# Evaluation results",
        "",
        f"- Model: {metadata['model']}",
        f"- Variant: {metadata['variant']}",
        f"- Run time UTC: {metadata['run_time_utc']}",
        f"- Business time: {metadata['business_time']}",
        f"- Source commit: {metadata['commit']}",
        f"- Questions SHA-256: {metadata['questions_sha256']}",
        f"- Completed: {len(report['results'])}/{metadata['total_questions']}",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]

    for status in ("PASS", "FAIL", "MANUAL_REVIEW", "ERROR"):
        lines.append(f"| {status} | {counts[status]} |")

    lines.extend(
        [
            "",
            "PASS requires successful automatic checks and a recorded human review.",
            "MANUAL_REVIEW is not counted as a pass.",
            "Raw tool traces and configuration are stored in results.json.",
        ]
    )

    for entry in report["results"]:
        review = entry.get("review") or {}

        lines.extend(
            [
                "",
                f"## {entry['case']['id']}: {final_status(entry)}",
                "",
                f"Question: {entry['case']['question']}",
                "",
                f"Expected: {entry['case']['expected_answer']}",
                "",
                f"Checks: `{json.dumps(entry['checks'])}`",
                "",
                f"Error: {entry.get('error') or 'None'}",
                "",
                f"Review: {review.get('reason', 'Pending')}",
                "",
                "~~~text",
                entry["answer"],
                "~~~",
            ]
        )

    (output_dir / "results.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="A-substring")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "eval")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    if args.report_only:
        saved_report = json.loads(
            (args.output_dir / "results.json").read_text(encoding="utf-8")
        )
        write_report(saved_report, args.output_dir)
        return

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise SystemExit("GEMINI_API_KEY is not configured")

    if not model:
        raise SystemExit("GEMINI_MODEL is not configured")

    questions_bytes = QUESTIONS_PATH.read_bytes()
    cases = json.loads(questions_bytes.decode("utf-8"))

    if len(cases) < 10:
        raise SystemExit("Evaluation requires at least 10 questions")

    refund_cases = [
        case
        for case in cases
        if case.get("expected_tool") == "calculate_refund"
        and "expected_amount_eur" in case
    ]

    if len(refund_cases) < 2:
        raise SystemExit("Evaluation requires at least 2 refund questions")

    if sum(case.get("expected_refusal") is True for case in cases) < 2:
        raise SystemExit("Evaluation requires at least 2 refusal questions")

    if len({case["id"] for case in cases}) != len(cases):
        raise SystemExit("Evaluation question IDs must be unique")

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).strip()

    report: dict = {
        "metadata": {
            "request_timeout_seconds": None,
            "model": model,
            "sdk_version": genai.__version__,
            "variant": args.variant,
            "max_steps": MAX_STEPS,
            "run_time_utc": datetime.now(UTC).isoformat(),
            "business_time": TIME_NOW.isoformat(),
            "commit": commit,
            "questions_sha256": hashlib.sha256(questions_bytes).hexdigest(),
            "system_instruction": SYSTEM_INSTRUCTION,
            "total_questions": len(cases),
        },
        "results": [],
    }

    with genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=None,
            client_args={"timeout": None},
            retry_options=types.HttpRetryOptions(attempts=0),
        ),
    ) as client:
        for index, case in enumerate(cases, start=1):
            print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
            trace: list[ToolTrace] = []
            started = perf_counter()

            entry: dict = {
                "case": case,
                "answer": "",
                "trace": trace,
                "checks": {},
                "error": None,
                "review": None,
            }

            try:
                entry["answer"] = run_agent(
                    case["question"],
                    client,
                    model,
                    max_steps=MAX_STEPS,
                    debug=False,
                    trace=trace,
                )
                entry["checks"] = check_answer(case, entry["answer"], trace)

            except (
                InteractionsAPIError,
                OSError,
                ValueError,
                KeyError,
                InvalidOperation,
                RuntimeError,
                TypeError,
            ) as error:
                entry["error"] = (
                    f"{type(error).__name__}; "
                    f"status={getattr(error, 'status_code', None)}"
                )

            entry["duration_seconds"] = round(perf_counter() - started, 3)
            report["results"].append(entry)

            write_report(report, args.output_dir)
            print(final_status(entry), flush=True)

    print(f"Results saved to {args.output_dir / 'results.md'}")


if __name__ == "__main__":
    main()
