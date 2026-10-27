import argparse
import json
from collections import Counter
from pathlib import Path

from .run_eval import final_status


def compare_reports(a: dict, b: dict) -> str:
    keys = (
        "model",
        "sdk_version",
        "questions_sha256",
        "system_instruction",
        "max_steps",
        "business_time",
        "request_timeout_seconds",
    )
    for key in keys:
        if a["metadata"].get(key) != b["metadata"].get(key):
            raise ValueError(f"Different configuration: {key}")

    if a["metadata"].get("scorer_version", 1) != b["metadata"].get("scorer_version", 1):
        raise ValueError("Different scorer versions")

    for report in (a, b):
        ids = [entry["case"]["id"] for entry in report["results"]]
        if len(ids) != report["metadata"]["total_questions"] or len(set(ids)) != len(
            ids
        ):
            raise ValueError("Incomplete run or duplicate question IDs")

    if [e["case"] for e in a["results"]] != [e["case"] for e in b["results"]]:
        raise ValueError("Different questions or question order")

    lines = [
        "# Retrieval comparison",
        "",
        "| Metric | A | B |",
        "| --- | ---: | ---: |",
    ]
    metrics = []

    for report in (a, b):
        entries = report["results"]
        counts = Counter(final_status(e) for e in entries)
        searches = [
            t for e in entries for t in e["trace"] if t["name"] == "search_policies"
        ]
        metrics.append(
            {
                **{
                    status: counts[status]
                    for status in ("PASS", "FAIL", "MANUAL_REVIEW", "ERROR")
                },
                "Tool calls": sum(len(e["trace"]) for e in entries),
                "Policy searches": len(searches),
                "Empty searches": sum(not t["result"] for t in searches),
                "Step-limit failures": sum(
                    not e["checks"].get("within_step_limit", True) for e in entries
                ),
            }
        )

    for metric, value in metrics[0].items():
        lines.append(f"| {metric} | {value} | {metrics[1][metric]} |")

    lines.extend(
        ["", "## Changed outcomes", "", "| Question | A | B |", "| --- | --- | --- |"]
    )
    for old, new in zip(a["results"], b["results"], strict=True):
        before, after = final_status(old), final_status(new)
        if before != after:
            lines.append(f"| {old['case']['id']} | {before} | {after} |")

    lines.extend(
        [
            "",
            "## Configuration",
            "",
            f"- A: {a['metadata']['variant']}, source commit {a['metadata']['commit']}",
            f"- B: {b['metadata']['variant']}, source commit {b['metadata']['commit']}",
            f"- Questions SHA-256: {a['metadata']['questions_sha256']}",
            f"- Scorer version: {a['metadata'].get('scorer_version', 1)}",
            "",
            "A uses substring matching. B uses tokenization, heading-weighted ranking and a top-three limit.",
            "This compares retrieval variants, not tokenization alone.",
            "One run per variant on development questions does not establish statistical significance.",
            "Empty searches can be appropriate for undocumented topics; fewer empty results alone do not prove better answers.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, type=Path)
    parser.add_argument("--b", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report_a = json.loads(args.a.read_text(encoding="utf-8"))
    report_b = json.loads(args.b.read_text(encoding="utf-8"))
    comparison = compare_reports(report_a, report_b)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(comparison, encoding="utf-8")
    print(comparison)


if __name__ == "__main__":
    main()
