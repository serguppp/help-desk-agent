from typing import TypedDict

from .config import POLICIES_PATH


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


def search_policies(query: str) -> list[PolicySections]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    query = query.strip().lower()
    sections: list[PolicySections] = []
    documents: list[PolicyDocument] = load_policies()
    for document in documents:
        sections.extend(split_sections(document["source"], document["text"]))

    heading_matches: list[PolicySections] = []
    text_matches: list[PolicySections] = []
    for section in sections:
        heading = section["heading"].lower()
        text = section["text"].lower()
        if query in heading:
            heading_matches.append(section)
        elif query in text:
            text_matches.append(section)

    return heading_matches + text_matches
