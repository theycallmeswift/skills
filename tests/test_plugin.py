"""Structural checks on the plugin: manifests parse and agree, the hook is wired, and every
skill's frontmatter carries a well-formed name matching its directory plus a description.

Params beyond those two are allowed but warn: they are harness-specific, so a skill using one owes
evals covering both a harness that honors it and a harness that drops it. The warning is the
reminder, not a gate. Add a param to `[tool.mechaswift] allowed_skill_frontmatter_params` in
pyproject.toml once that is settled."""

from __future__ import annotations

import json
import os
import re
import tomllib
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (ROOT / "skills").glob("*/") if (p / "SKILL.md").exists())

REQUIRED_FIELDS = {"name", "description"}
"""Frontmatter every skill must declare. Every harness reads both."""


class HarnessSpecificFieldWarning(UserWarning):
    """A skill declares frontmatter that only some harnesses honor."""


def _allowed_frontmatter_params() -> frozenset[str]:
    """Read the frontmatter params a skill may declare without warning.

    Returns:
        Param names from `[tool.mechaswift] allowed_skill_frontmatter_params` in pyproject.toml,
        falling back to the required pair when the key is absent.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    table = config.get("tool", {}).get("mechaswift", {})
    return frozenset(table.get("allowed_skill_frontmatter_params", REQUIRED_FIELDS))


def _unexpected_frontmatter(fields: dict[str, str], allowed: frozenset[str]) -> list[str]:
    """Return declared frontmatter params that the allowlist does not cover.

    Args:
        fields: Top-level frontmatter params of the skill.
        allowed: Param names permitted without warning.

    Returns:
        Sorted param names to warn about; empty when every param is allowed.
    """
    return sorted(set(fields) - allowed)


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
    assert REQUIRED_FIELDS <= set(fields), f"missing {sorted(REQUIRED_FIELDS - set(fields))}"
    assert fields["name"] == skill.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"])
    assert fields["description"], "description must not be empty"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_frontmatter_beyond_the_allowlist_warns(skill: Path):
    """Warn, don't fail: a harness-specific param is a deliberate choice that owes evals."""
    fields = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    unexpected = _unexpected_frontmatter(fields, _allowed_frontmatter_params())

    if unexpected:
        warnings.warn(
            f"{skill.name}: harness-specific frontmatter {unexpected}. Only some harnesses honor "
            "these, so this skill owes evals covering one that honors them and one that drops "
            "them. Once settled, add them to [tool.mechaswift] "
            "allowed_skill_frontmatter_params.",
            HarnessSpecificFieldWarning,
            stacklevel=2,
        )


def test_frontmatter_outside_the_allowlist_is_reported():
    fields = {"name": "x", "description": "d", "context": "fork", "agent": "Explore"}
    assert _unexpected_frontmatter(fields, frozenset(REQUIRED_FIELDS)) == ["agent", "context"]


def test_allowlisted_frontmatter_is_silent():
    fields = {"name": "x", "description": "d", "context": "fork", "agent": "Explore"}
    allowed = frozenset(REQUIRED_FIELDS | {"context", "agent"})
    assert _unexpected_frontmatter(fields, allowed) == []


def test_required_frontmatter_alone_is_silent():
    fields = {"name": "x", "description": "d"}
    assert _unexpected_frontmatter(fields, _allowed_frontmatter_params()) == []


def test_allowlist_covers_the_required_fields():
    """Dropping name or description from the allowlist would warn on every skill at once."""
    missing = REQUIRED_FIELDS - _allowed_frontmatter_params()
    assert not missing, f"allowed_skill_frontmatter_params omits {sorted(missing)}"
