"""Structural checks on the plugin: manifests parse and agree, the hook is wired, and every
skill's frontmatter carries a well-formed name matching its directory plus a description.

Fields beyond those two are allowed but warn: they are harness-specific, so a skill that uses one
owes evals covering both the harness that honors it and a harness that ignores it. The warning is
the reminder, not a gate — see PORTABLE_FIELDS."""

from __future__ import annotations

import json
import os
import re
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (ROOT / "skills").glob("*/") if (p / "SKILL.md").exists())

PORTABLE_FIELDS = {"name", "description"}
"""Fields every harness reads. Anything else is honored by some harnesses and dropped by others."""


class HarnessSpecificFieldWarning(UserWarning):
    """A skill declares frontmatter that only some harnesses honor."""


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _frontmatter(text: str) -> dict[str, str]:
    """Parse a SKILL.md frontmatter block into top-level key -> value.

    Nested blocks (`hooks`, `metadata`) are recorded by key with an empty value; their indented
    bodies are skipped rather than rejected, since harness-specific fields may be YAML maps.

    Args:
        text: Full SKILL.md contents.

    Returns:
        Top-level frontmatter fields in declaration order.
    """
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md must open with a --- frontmatter block"
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t", "-", "#")):
            continue
        key, sep, value = line.partition(":")
        assert sep, f"unexpected frontmatter line: {line!r}"
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
def test_skill_frontmatter_names_and_describes_the_skill(skill: Path):
    fields = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    assert PORTABLE_FIELDS <= set(fields), f"missing {sorted(PORTABLE_FIELDS - set(fields))}"
    assert fields["name"] == skill.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"])
    assert fields["description"], "description must not be empty"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_frontmatter_beyond_name_and_description_warns(skill: Path):
    """Warn, don't fail: extra fields are a deliberate choice that owes cross-harness evals."""
    fields = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    extra = sorted(set(fields) - PORTABLE_FIELDS)
    if extra:
        warnings.warn(
            f"{skill.name}: harness-specific frontmatter {extra}. Only some harnesses honor "
            "these, so this skill owes evals covering one that honors them and one that drops "
            "them.",
            HarnessSpecificFieldWarning,
            stacklevel=2,
        )
