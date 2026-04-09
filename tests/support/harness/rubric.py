from pathlib import Path


def parse_rubric_file(path: Path) -> list[dict]:
    """Return [{text, critical}, ...]. Missing file returns []."""
    if not path.exists():
        return []
    return parse_rubric_text(path.read_text())


def parse_rubric_text(text: str) -> list[dict]:
    items: list[dict] = []
    current_section: str | None = None  # "critical" | "optional" | None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading == "Critical":
                current_section = "critical"
            elif heading == "Optional":
                current_section = "optional"
            else:
                current_section = None
            continue
        if current_section is None:
            continue
        if line.startswith("- "):
            bullet = line[2:].strip()
            if bullet:
                items.append({"text": bullet, "critical": current_section == "critical"})
    return items
