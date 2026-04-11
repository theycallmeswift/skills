import sys
from pathlib import Path

import yaml


def parse_prompt(path):
    """Read a prompt file, strip YAML frontmatter if present.

    Returns (frontmatter_dict_or_None, body_string).
    Pass "-" to read from stdin.
    """
    if str(path) == "-":
        content = sys.stdin.read()
    else:
        content = Path(path).read_text(encoding="utf-8")

    if not content.startswith("---\n"):
        return None, content

    end = content.find("\n---\n", 4)
    if end == -1:
        return None, content

    frontmatter_raw = content[4:end]
    body = content[end + 5:].lstrip("\n")

    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError:
        return None, content

    return frontmatter, body
