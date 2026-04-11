import csv
import io
import sys
from pathlib import Path

import yaml


def read_prompt(path):
    """Read prompt content from a file path or stdin ("-")."""
    if str(path) == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def parse_prompt(content):
    """Strip YAML frontmatter if present.

    Returns (frontmatter_dict_or_None, body_string).
    """
    if not content.startswith("---\n"):
        return None, content

    end = content.find("\n---\n", 4)
    if end == -1:
        return None, content

    frontmatter_raw = content[4:end]
    body = content[end + 5 :].lstrip("\n")

    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError:
        return None, content

    return frontmatter, body


def load_csv(path):
    """Load CSV file, return (headers, rows).

    Each row is a dict mapping header name to value.
    Raises ValueError if no headers or no data rows.
    """
    text = Path(path).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no headers")
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file has no data rows")
    return list(reader.fieldnames), rows
