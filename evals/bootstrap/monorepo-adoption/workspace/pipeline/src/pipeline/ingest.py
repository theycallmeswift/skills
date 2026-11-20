import json
import os
import sys


def load_sources(path):
    with open(os.path.join(path, "sources.json")) as f:
        return json.load(f)


def active(sources):
    return [s for s in sources if s.get("enabled", True)]


def build_digest(items, limit=10):
    lines = []
    for item in items[:limit]:
        lines.append("- %s (%s)" % (item["title"], item["source"]))
    return "\n".join(lines)
