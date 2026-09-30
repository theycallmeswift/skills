"""Structural checks on the plugin: manifests parse and agree, the hook is wired, and every
skill's frontmatter carries a well-formed name matching its directory plus a description.

Params beyond those two are allowed but warn: they are harness-specific, so a skill using one owes
evals covering both a harness that honors it and a harness that drops it. The warning is the
reminder, not a gate. Once that is settled, allow the param in pyproject.toml — repo-wide under
`[tool.mechaswift] allowed_skill_frontmatter_params`, or for one skill under
`[tool.mechaswift.skills.<name>]`. With nothing configured the allowlist is name + description."""

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

MAX_DESCRIPTION_CHARS = 1024
"""Spec cap on `description`. Harnesses that enforce it truncate the tail, which is where the
"Don't use for…" exclusions that drive routing live."""


class HarnessSpecificFieldWarning(UserWarning):
    """A skill declares frontmatter that only some harnesses honor."""


def _mechaswift_config() -> dict:
    """Read the `[tool.mechaswift]` table from pyproject.toml."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return config.get("tool", {}).get("mechaswift", {})


def _resolve_allowed_params(config: dict, skill_name: str) -> frozenset[str]:
    """Resolve the frontmatter params one skill may declare without warning.

    The repo-wide `allowed_skill_frontmatter_params` list applies to every skill and defaults to
    REQUIRED_FIELDS when unset. A `[tool.mechaswift.skills.<name>]` table may name further params,
    which extend the repo-wide list for that skill only rather than replacing it.

    Args:
        config: Parsed `[tool.mechaswift]` table.
        skill_name: Directory name of the skill being checked.

    Returns:
        Param names allowed for this skill.
    """
    key = "allowed_skill_frontmatter_params"
    allowed = frozenset(config.get(key, REQUIRED_FIELDS))

    per_skill = config.get("skills", {}).get(skill_name, {})
    return allowed | frozenset(per_skill.get(key, ()))


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
def test_skill_description_fits_the_length_cap(skill: Path):
    description = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))["description"]
    assert description not in {">", ">-", "|", "|-"}, "keep description on one line to measure it"
    assert len(description) <= MAX_DESCRIPTION_CHARS, (
        f"description is {len(description)} chars; cap is {MAX_DESCRIPTION_CHARS}"
    )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_frontmatter_beyond_the_allowlist_warns(skill: Path):
    """Warn, don't fail: a harness-specific param is a deliberate choice that owes evals."""
    fields = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    allowed = _resolve_allowed_params(_mechaswift_config(), skill.name)
    unexpected = _unexpected_frontmatter(fields, allowed)

    if unexpected:
        warnings.warn(
            f"{skill.name}: harness-specific frontmatter {unexpected}. Only some harnesses honor "
            "these, so this skill owes evals covering one that honors them and one that drops "
            f"them. Once settled, allow them in allowed_skill_frontmatter_params — repo-wide "
            f"under [tool.mechaswift], or here only under [tool.mechaswift.skills.{skill.name}].",
            HarnessSpecificFieldWarning,
            stacklevel=2,
        )


EXTRA_FRONTMATTER = {"name": "x", "description": "d", "context": "fork", "agent": "Explore"}


def test_frontmatter_outside_the_allowlist_is_reported():
    allowed = _resolve_allowed_params({}, "x")
    assert _unexpected_frontmatter(EXTRA_FRONTMATTER, allowed) == ["agent", "context"]


def test_unset_config_defaults_to_name_and_description():
    assert _resolve_allowed_params({}, "x") == frozenset(REQUIRED_FIELDS)


def test_repo_wide_allowlist_silences_every_skill():
    config = {"allowed_skill_frontmatter_params": ["name", "description", "context", "agent"]}
    assert _unexpected_frontmatter(EXTRA_FRONTMATTER, _resolve_allowed_params(config, "x")) == []


def test_per_skill_allowlist_extends_the_repo_wide_one():
    """Per-skill params add to the repo-wide list; name and description need no restating."""
    config = {"skills": {"x": {"allowed_skill_frontmatter_params": ["context", "agent"]}}}
    assert _unexpected_frontmatter(EXTRA_FRONTMATTER, _resolve_allowed_params(config, "x")) == []


def test_per_skill_allowlist_does_not_leak_to_other_skills():
    config = {"skills": {"x": {"allowed_skill_frontmatter_params": ["context", "agent"]}}}
    allowed = _resolve_allowed_params(config, "other")
    assert _unexpected_frontmatter(EXTRA_FRONTMATTER, allowed) == ["agent", "context"]


def test_allowlist_covers_the_required_fields():
    """Dropping name or description from the allowlist would warn on every skill at once."""
    missing = REQUIRED_FIELDS - _resolve_allowed_params(_mechaswift_config(), "any")
    assert not missing, f"allowed_skill_frontmatter_params omits {sorted(missing)}"


def test_per_skill_allowlist_entries_name_real_skills():
    """A stale entry silences a skill that no longer exists, so keep the table honest."""
    unknown = set(_mechaswift_config().get("skills", {})) - {p.name for p in SKILLS}
    assert not unknown, f"[tool.mechaswift.skills] names unknown skills: {sorted(unknown)}"
