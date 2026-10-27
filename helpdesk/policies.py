import re
from typing import TypedDict

from .config import HEADING_WEIGHT, MAX_RESULTS, POLICIES_PATH, STOP_WORDS

TOKEN_ALIASES = {
    "bikes": "bike",
    "buy": "sell",
    "purchase": "sell",
    "sales": "sell",
    "payment": "pay",
    "payments": "pay",
}

POLICY_DOCUMENT_NAMES = ("faq.md", "prices.md", "cancellations.md")


class PolicyDocument(TypedDict):
    source: str
    text: str


class PolicySections(TypedDict):
    source: str
    heading: str
    text: str


def split_sections(file_name: str, text: str) -> list[PolicySections]:
    sections: list[PolicySections] = []
    heading = ""
    text_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith(("# ", "## ")):
            section_text = "\n".join(text_lines).strip()

            if heading and section_text:
                sections.append(
                    PolicySections(
                        source=file_name,
                        heading=heading,
                        text=section_text,
                    )
                )

            heading = line[2:].strip()
            text_lines = []
        else:
            text_lines.append(line)

    section_text = "\n".join(text_lines).strip()

    if heading and section_text:
        sections.append(
            PolicySections(
                source=file_name,
                heading=heading,
                text=section_text,
            )
        )

    return sections


def load_policies() -> list[PolicyDocument]:
    documents: list[PolicyDocument] = []

    paths = sorted(POLICIES_PATH.glob("*.md"))

    if not paths:
        raise FileNotFoundError("No CityWheels policy documents found")

    for path in paths:
        text = path.read_text(encoding="utf-8")
        documents.append(PolicyDocument(source=path.name, text=text))

    return documents


def tokenize(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", text.casefold())) - STOP_WORDS
    return {TOKEN_ALIASES.get(token, token) or token for token in tokens}


def search_policies(query: str) -> list[PolicySections]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    sections: list[PolicySections] = []
    documents: list[PolicyDocument] = load_policies()
    for document in documents:
        sections.extend(split_sections(document["source"], document["text"]))

    ranked: list[tuple[int, PolicySections]] = []

    for section in sections:
        heading_tokens = tokenize(section["heading"])
        text_tokens = tokenize(section["text"])

        heading_matches = len(query_tokens & heading_tokens)
        text_matches = len(query_tokens & text_tokens)
        score = HEADING_WEIGHT * heading_matches + text_matches

        if score > 0:
            ranked.append((score, section))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [section for _, section in ranked[:MAX_RESULTS]]


def read_policy_document(file_name: str) -> PolicyDocument:
    if not isinstance(file_name, str) or file_name not in POLICY_DOCUMENT_NAMES:
        raise ValueError("file_name must be faq.md, prices.md or cancellations.md")

    path = POLICIES_PATH / file_name
    return PolicyDocument(source=file_name, text=path.read_text(encoding="utf-8"))
