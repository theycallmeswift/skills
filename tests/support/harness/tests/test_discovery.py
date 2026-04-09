import json
from pathlib import Path

import pytest

from tests.support.harness.discovery import EvalSuite, build_run_plans, discover_suites, load_eval_file
from tests.support.harness.models import EvalCase


def _write_suite(tmp_path: Path, cleanup: list[str]) -> Path:
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [
                    {
                        "id": "c1",
                        "turns": ["hi"],
                        "cleanup": cleanup,
                    }
                ],
            }
        )
    )
    return f


def test_cleanup_allows_safe_references_specs(tmp_path):
    f = _write_suite(tmp_path, ["references/specs/2026-*.md"])
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].cleanup == ["references/specs/2026-*.md"]


def test_cleanup_allows_tmp_subpaths(tmp_path):
    f = _write_suite(tmp_path, ["tmp/foo/*"])
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].cleanup == ["tmp/foo/*"]


def test_cleanup_rejects_absolute_path(tmp_path):
    f = _write_suite(tmp_path, ["/etc/passwd"])
    with pytest.raises(ValueError, match="absolute"):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_parent_traversal(tmp_path):
    f = _write_suite(tmp_path, ["../secrets/*"])
    with pytest.raises(ValueError, match=r"\.\."):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_unsafe_root(tmp_path):
    f = _write_suite(tmp_path, ["skills/*"])
    with pytest.raises(ValueError, match="allowed roots"):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_bare_star(tmp_path):
    f = _write_suite(tmp_path, ["*"])
    with pytest.raises(ValueError, match="allowed roots"):
        load_eval_file(f, kind="skill")


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_load_skill_eval_file():
    suite = load_eval_file(FIXTURES / "sample-skill-eval.json", kind="skill")
    assert isinstance(suite, EvalSuite)
    assert suite.name == "ghostwrite"
    assert suite.kind == "skill"
    assert len(suite.cases) == 1
    case = suite.cases[0]
    assert case.id == "sponsor-email"
    assert case.turns == ["Rewrite this in Swift's voice: hello world"]
    assert case.files == []
    assert case.assertions == [{"contains": "hello"}]
    assert case.cleanup == []
    assert case.intent == "lift"


def test_load_core_eval_file():
    suite = load_eval_file(FIXTURES / "sample-core-eval.json", kind="core")
    assert suite.kind == "core"
    case = suite.cases[0]
    assert case.cleanup == ["tmp/fake-repo"]


def test_missing_name_raises_clear_error(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({"evals": [{"id": "c1", "turns": ["hi"]}]}))
    with pytest.raises(ValueError, match="missing 'name'"):
        load_eval_file(f, kind="skill")


def test_missing_evals_raises_clear_error(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({"name": "demo"}))
    with pytest.raises(ValueError, match="missing 'evals'"):
        load_eval_file(f, kind="skill")


def test_schema_rejects_unknown_top_level_key(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [{"id": "c1", "turns": ["hi"]}],
                "random_typo_key": 42,
            }
        )
    )
    with pytest.raises(ValueError, match="schema validation failed"):
        load_eval_file(f, kind="skill")


def test_schema_rejects_assertion_with_multiple_keys(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [
                    {
                        "id": "c1",
                        "turns": ["hi"],
                        "assertions": [{"contains": "x", "tool_called": "y"}],
                    }
                ],
            }
        )
    )
    with pytest.raises(ValueError, match="schema validation failed"):
        load_eval_file(f, kind="skill")


def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "demo.json"
    p.write_text(json.dumps(data))
    return p


def test_run_plan_carries_tier(tmp_path):
    suite = EvalSuite(
        name="demo",
        kind="core",
        source_path=tmp_path / "demo.json",
        cases=[EvalCase(id="c1", turns=["hi"])],
    )
    plans = build_run_plans([suite], project_root=tmp_path, baseline=False, tier="eval")
    assert plans[0].tier == "eval"


def test_flat_discovery_finds_skill_suite(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "ghostwrite.json").write_text(
        json.dumps({"name": "ghostwrite", "evals": [{"id": "x", "turns": ["hi"]}]})
    )
    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    assert len(suites) == 1
    assert suites[0].kind == "skill"
    assert suites[0].name == "ghostwrite"


def test_flat_discovery_treats_unknown_stem_as_core(tmp_path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "skill-triggers.json").write_text(
        json.dumps({"name": "skill-triggers", "evals": [{"id": "x", "turns": ["hi"]}]})
    )
    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    assert suites[0].kind == "core"


def test_schema_accepts_new_primitives(tmp_path):
    data = {
        "name": "demo",
        "evals": [
            {
                "id": "c1",
                "turns": ["hello"],
                "assertions": [
                    {"regex": "hi", "min": 1, "max": 3, "on": "final_message"},
                    {"not_regex": "bad"},
                    {"contains": "hello"},
                    {"contains_all": ["a", "b"]},
                    {"not_contains": "bad"},
                    {"output_len_lte": 100},
                    {"output_len_gte": 10},
                    {"token_usage_lte": 1000},
                    {"skill_invoked": "ghostwrite"},
                    {"skill_not_invoked": "summarize"},
                    {"trace_order": ["Read", "Write"]},
                    {"trace_count_lte": {"tool": "Bash", "n": 3}},
                    {"turn_count_lte": 1},
                    {"files_written_include": "*.md"},
                    {"files_written_exclude": "*.py"},
                    {"files_written_count": 0},
                    {"file_contains": {"path": "*.md", "text": "ok"}},
                    {"script_name": "ghostwrite"},
                ],
            }
        ],
    }
    path = _write(tmp_path, data)
    suite = load_eval_file(path, kind="skill")
    assert suite.name == "demo"
    assert len(suite.cases[0].assertions) == 18


def test_schema_rejects_shared_assertions(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "shared_assertions": [{"contains": "x"}],
                "evals": [{"id": "c1", "turns": ["hi"]}],
            }
        )
    )
    with pytest.raises(ValueError, match="schema validation failed"):
        load_eval_file(f, kind="skill")


def test_build_run_plans_skill_with_baseline_flat(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "ghostwrite.json").write_text(
        json.dumps({
            "name": "ghostwrite",
            "evals": [{"id": "sponsor-email", "turns": ["hi"], "intent": "lift", "assertions": [{"contains": "x"}]}],
        })
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)

    assert len(plans) == 2
    by_variant = {p.variant: p for p in plans}
    assert "with_skill" in by_variant and "baseline" in by_variant

    with_skill = by_variant["with_skill"]
    assert with_skill.suite_name == "ghostwrite"
    assert with_skill.turns[0].startswith("Before responding, read and follow skills/ghostwrite/SKILL.md.")
    assert (tmp_path / "skills" / "ghostwrite") in with_skill.context_paths

    baseline = by_variant["baseline"]
    assert baseline.turns == ["hi"]
    assert (tmp_path / "skills" / "ghostwrite") not in baseline.context_paths


def test_regression_intent_emits_only_with_skill_flat(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "ghostwrite.json").write_text(
        json.dumps({
            "name": "ghostwrite",
            "evals": [{"id": "c1", "turns": ["hi"], "intent": "regression", "assertions": [{"contains": "x"}]}],
        })
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    assert plans[0].variant == "with_skill"


def test_build_run_plans_core_flat(tmp_path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "no-ai-attribution.json").write_text(
        json.dumps({
            "name": "no-ai-attribution",
            "evals": [{"id": "c1", "turns": ["hi"], "cleanup": ["tmp/fake-repo"], "assertions": [{"contains": "x"}]}],
        })
    )
    (tmp_path / "AGENTS.md").write_text("# project context")

    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    assert plans[0].variant == "run"
    assert plans[0].suite_name == "no-ai-attribution"
