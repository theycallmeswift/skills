"""Structural checks on the plugin: manifests parse and agree, the hook is wired, and every
skill's frontmatter is the portable name + description pair with name matching its directory."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (ROOT / "skills").glob("*/") if (p / "SKILL.md").exists())


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md must open with a --- frontmatter block"
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        assert sep and not line.startswith(" "), f"unexpected frontmatter line: {line!r}"
        fields[key.strip()] = value.strip()
    return fields


def test_marketplace_lists_the_plugin_manifest_by_name():
    plugin = _load(".claude-plugin/plugin.json")
    marketplace = _load(".claude-plugin/marketplace.json")
    assert marketplace["name"] == "mechaswift"
    names = [p["name"] for p in marketplace["plugins"]]
    assert names == [plugin["name"]]
    assert marketplace["plugins"][0]["source"] == "./"


def test_hooks_reference_an_executable_script_under_plugin_root():
    hooks = _load("hooks/hooks.json")["hooks"]
    for event in hooks.values():
        for matcher in event:
            for hook in matcher["hooks"]:
                command = hook["command"].strip('"')
                assert command.startswith("${CLAUDE_PLUGIN_ROOT}/"), command
                script = ROOT / command.removeprefix("${CLAUDE_PLUGIN_ROOT}/")
                assert script.exists(), script
                assert os.access(script, os.X_OK), f"{script} is not executable"


def test_skills_sh_groupings_name_real_skills():
    groupings = _load("skills.sh.json")["groupings"]
    known = {p.name for p in SKILLS}
    for group in groupings:
        missing = set(group["skills"]) - known
        assert not missing, f"{group['title']} names unknown skills: {sorted(missing)}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_frontmatter_is_portable(skill: Path):
    fields = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    assert set(fields) == {"name", "description"}, sorted(fields)
    assert fields["name"] == skill.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"])
    assert 0 < len(fields["description"]) <= 1024
