from typing import TypedDict

from .config import POLICIES_PATH


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


def load_policies() -> list[dict[str, str]]:
    documents = []

    for path in sorted(POLICIES_PATH.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        documents.append(
            {
                "source": path.name,
                "text": text,
            }
        )

    return documents
