import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median

from helpdesk.config import PROJECT_ROOT

from .run_eval import final_status


def summarize(report: dict) -> dict:
    entries = report["results"]
    counts = Counter(final_status(entry) for entry in entries)
    searches = [
        call
        for entry in entries
        for call in entry["trace"]
        if call["name"] == "search_policies"
    ]
    durations = [
        entry["duration_seconds"] for entry in entries if "duration_seconds" in entry
    ]
    return {
        "completed": len(entries),
        "total": report["metadata"]["total_questions"],
        "counts": counts,
        "automatic_ok": sum(
            not entry.get("error")
            and bool(entry.get("checks"))
            and all(entry["checks"].values())
            for entry in entries
        ),
        "tool_calls": sum(len(entry["trace"]) for entry in entries),
        "searches": len(searches),
        "empty_searches": sum(not call["result"] for call in searches),
        "document_reads": sum(
            call["name"] == "read_policy_document"
            for entry in entries
            for call in entry["trace"]
        ),
        "step_limits": sum(
            not entry["checks"].get("within_step_limit", True) for entry in entries
        ),
        "total_seconds": sum(durations),
        "median_seconds": median(durations) if durations else 0,
    }


def compare_reports(reports: dict[str, dict]) -> str:
    if not reports:
        raise ValueError("No evaluation reports found")
    groups: dict[tuple[str, int, int], dict[str, dict]] = {}
    for name, report in sorted(reports.items()):
        metadata = report["metadata"]
        entries = report["results"]
        ids = [entry["case"]["id"] for entry in entries]
        if len(ids) != len(set(ids)) or len(ids) > metadata["total_questions"]:
            raise ValueError(f"Invalid question IDs or result count: {name}")
        key = (
            metadata["questions_sha256"],
            metadata["total_questions"],
            metadata.get("scorer_version", 1),
        )
        groups.setdefault(key, {})[name] = report

    lines = [
        "# Evaluation comparison",
        "",
        "Scores come from saved automatic checks and recorded qualitative reviews. Model names come from metadata, not folder names.",
        "",
        "## Summary",
        "",
        "| Run | Recorded model | Questions | Scorer | PASS | FAIL | Pending | ERROR | Pass rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, report in sorted(reports.items()):
        result = summarize(report)
        counts = result["counts"]
        reviewed = (
            result["completed"] == result["total"] and not counts["MANUAL_REVIEW"]
        )
        rate = (
            f"{100 * counts['PASS'] / result['total']:.1f}%"
            if reviewed and result["total"]
            else "Pending/incomplete"
        )
        metadata = report["metadata"]
        lines.append(
            f"| [{name}](runs/{name}/results.md) | `{metadata['model']}` | "
            f"{result['completed']}/{result['total']} | {metadata.get('scorer_version', 1)} | "
            f"{counts['PASS']} | {counts['FAIL']} | {counts['MANUAL_REVIEW']} | {counts['ERROR']} | {rate} |"
        )
    for key, group in sorted(
        groups.items(), key=lambda item: (-item[0][2], -item[0][1], item[0][0])
    ):
        question_hash, total, scorer = key
        lines.extend(
            [
                "",
                f"## {total} questions, scorer v{scorer}",
                "",
                f"Question-file SHA-256: `{question_hash}`.",
                "",
                "| Run | Checks OK | Tool calls | Searches | Empty searches | Document reads | Step limits | Total case time (s) | Median case time (s) |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        cases: dict[str, dict] = {}
        for name, report in group.items():
            for entry in report["results"]:
                case = entry["case"]
                if case["id"] in cases and cases[case["id"]] != case:
                    raise ValueError(
                        "Different expectations under the same question hash"
                    )
                cases[case["id"]] = case
            result = summarize(report)
            lines.append(
                f"| {name} | {result['automatic_ok']}/{result['completed']} | {result['tool_calls']} | "
                f"{result['searches']} | {result['empty_searches']} | {result['document_reads']} | "
                f"{result['step_limits']} | {result['total_seconds']:.2f} | {result['median_seconds']:.2f} |"
            )
        if len(group) > 1:
            names = list(group)
            lines.extend(
                [
                    "",
                    "### Different outcomes",
                    "",
                    "| Question | " + " | ".join(names) + " |",
                    "| --- | " + " | ".join("---" for _ in names) + " |",
                ]
            )
            outcomes = {
                name: {
                    entry["case"]["id"]: final_status(entry)
                    for entry in report["results"]
                }
                for name, report in group.items()
            }
            changed = False
            for case_id in cases:
                values = [outcomes[name].get(case_id, "Not run") for name in names]
                if len(set(values)) > 1:
                    changed = True
                    lines.append(f"| `{case_id}` | " + " | ".join(values) + " |")
            if not changed:
                lines.append(
                    "| No status differences | " + " | ".join("-" for _ in names) + " |"
                )

    lines.extend(["", "## Recorded failures", ""])
    for name, report in sorted(reports.items()):
        failed = [
            entry["case"]["id"]
            for entry in report["results"]
            if final_status(entry) in {"FAIL", "ERROR"}
        ]
        if failed:
            lines.append(
                f"- [{name}](runs/{name}/results.md): "
                + ", ".join(f"`{case_id}`" for case_id in failed)
                + "."
            )
    lines.extend(
        [
            "",
            "## Configuration",
            "",
            "| Run | Model | Source commit | SDK | Max rounds | Request timeout (s) | Prompt SHA-256 | Run time UTC |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for name, report in sorted(reports.items()):
        metadata = report["metadata"]
        prompt_hash = hashlib.sha256(
            metadata["system_instruction"].encode()
        ).hexdigest()
        timeout = metadata.get("request_timeout_seconds", "Not recorded")
        timeout_text = "Disabled" if timeout is None else str(timeout)
        lines.append(
            f"| [{name}](runs/{name}/results.json) | `{metadata['model']}` | `{metadata['commit']}` | "
            f"{metadata['sdk_version']} | {metadata['max_steps']} | {timeout_text} | `{prompt_hash}` | {metadata['run_time_utc']} |"
        )
    lines.extend(
        [
            "",
            "## Changes and interpretation",
            "",
            "- A: literal substring retrieval. B: tokenization, heading-weighted ranking and a top-three limit, with the same prompt as A. This compares all retrieval changes together.",
            "- C: token aliases and a changed prompt. D: structured refund components/methods, full-document reading and revised instructions. Improvements cannot be attributed to one change alone.",
            "- Use scorer-v2 A/B reports for the 45-question comparison. Rescored reports reuse original answers and traces; they are not additional model runs.",
            "- B changes from 39/45 to 40/45 after recognizing a zero refund expressed in words. This corrects the evaluator, not the agent.",
            "- The original 22-question run and the new 15-question holdout are separate datasets. Do not compare their percentages directly with the 45-question development set.",
            "- The D model comparisons have matching recorded prompts, SDK, business time and request budget. Check the configuration table before attributing differences to a model.",
            "- Both D models score 43/45 on development questions and 14/15 on holdout questions, but fail different cases. There is no quality winner from these single runs.",
            "- On the 45-question set, D 3.5 fails the cat step limit and the unusual payment question. D 3.8 fails the cat step limit and adds an unsupported universal Revolut-card acceptance claim.",
            "- On holdout, 3.5 incorrectly asserts that no student rate exists; 3.8 reaches the step limit on phone holders. These show that reading the full document does not guarantee correct reasoning or stopping.",
            "",
            "## Limits of the comparison",
            "",
            "- The 45 development questions guided implementation changes. The holdout uses new questions from the same source documents, not an external benchmark.",
            "- Qualitative reviews assess the whole answer, including unsupported additions. Some correct central answers omit secondary details; their review notes explain the judgment.",
            "- Automatic checks alone do not establish correctness. Pending review is not a pass, and safe step-limit fallbacks remain failures.",
            "- One run per configuration is insufficient to establish statistical significance or reliability on unseen questions.",
            "- Wall times depend on service load, network conditions and the number of model rounds. They are observations, not a controlled performance benchmark. No token-based cost measurements were recorded.",
            "- A source commit does not capture uncommitted evaluator changes. The D holdout runs used --questions before that change was committed; question and prompt hashes are preserved.",
            "- Earlier scoring is retained in [comparison-original.md](comparison-original.md) and [comparison-rescored.md](comparison-rescored.md). Original results and rescored copies remain available.",
            "- API quota and billing troubleshooting probes are not evaluation runs and are not included in these tables.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=PROJECT_ROOT / "eval" / "runs")
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "eval" / "comparison.md"
    )
    args = parser.parse_args()
    reports = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.runs_dir.glob("*/results.json"))
    }
    comparison = compare_reports(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(comparison, encoding="utf-8")
    print(f"Saved comparison of {len(reports)} reports to {args.output}")


if __name__ == "__main__":
    main()
