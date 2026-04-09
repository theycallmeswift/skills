import json
from pathlib import Path

import pytest

from tests.support.harness.discovery import EvalSuite, load_eval_file


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


def test_grader_input_limit_is_loaded(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [
                    {
                        "id": "c1",
                        "turns": ["hi"],
                        "grader_input_limit": 8000,
                        "assertions": [{"text": "x"}],
                    },
                    {
                        "id": "c2",
                        "turns": ["hi"],
                        "assertions": [{"text": "x"}],
                    },
                ],
            }
        )
    )
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].grader_input_limit == 8000
    assert suite.cases[1].grader_input_limit is None


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


def test_shared_assertions_are_prepended_to_each_case(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "shared_assertions": [
                    {"text": "Output is non-empty"},
                    {"text": "Output has a heading"},
                ],
                "evals": [
                    {
                        "id": "c1",
                        "turns": ["hi"],
                        "assertions": [{"text": "Output mentions cats"}],
                    },
                    {
                        "id": "c2",
                        "turns": ["hi"],
                        "assertions": [{"text": "Output mentions dogs"}],
                    },
                ],
            }
        )
    )
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == [
        "Output is non-empty",
        "Output has a heading",
        "Output mentions cats",
    ]
    assert [a["text"] for a in suite.cases[1].assertions] == [
        "Output is non-empty",
        "Output has a heading",
        "Output mentions dogs",
    ]


def test_case_can_opt_out_of_shared_assertions(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "shared_assertions": [{"text": "shared one"}],
                "evals": [
                    {
                        "id": "opted-out",
                        "turns": ["hi"],
                        "use_shared_assertions": False,
                        "assertions": [{"text": "own one"}],
                    },
                ],
            }
        )
    )
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == ["own one"]


def test_no_shared_assertions_key_works_as_before(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [
                    {"id": "c1", "turns": ["hi"], "assertions": [{"text": "only"}]},
                ],
            }
        )
    )
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == ["only"]


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
    assert case.assertions == [{"text": "Output is short"}]
    assert case.grader_model is None
    assert case.cleanup == []
    assert case.intent == "lift"


def test_load_core_eval_file():
    suite = load_eval_file(FIXTURES / "sample-core-eval.json", kind="core")
    assert suite.kind == "core"
    case = suite.cases[0]
    assert case.grader_model == "claude-haiku-4-5-20251001"
    assert case.cleanup == ["tmp/fake-repo"]


def test_discover_walks_tests_tree(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites

    suites = discover_suites(tmp_path / "tests")
    assert len(suites) == 2
    by_name = {s.name: s for s in suites}
    assert by_name["ghostwrite"].kind == "skill"
    assert by_name["no-ai-attribution"].kind == "core"


def test_discover_filters_by_name(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites

    suites = discover_suites(tmp_path / "tests", names=["ghostwrite"])
    assert len(suites) == 1
    assert suites[0].name == "ghostwrite"


def test_build_run_plans_skill_with_baseline(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import build_run_plans, discover_suites

    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)

    assert len(plans) == 2
    by_variant = {p.variant: p for p in plans}
    assert "with_skill" in by_variant and "baseline" in by_variant

    with_skill = by_variant["with_skill"]
    assert with_skill.suite_name == "ghostwrite"
    assert with_skill.case_id == "sponsor-email"
    assert with_skill.turns[0].startswith(
        "Before responding, read and follow skills/ghostwrite/SKILL.md."
    )
    assert "Rewrite this" in with_skill.turns[0]
    assert len(with_skill.turns) == 1
    assert (tmp_path / "skills" / "ghostwrite") in with_skill.context_paths
    assert (tmp_path / "AGENTS.md") in with_skill.context_paths

    baseline = by_variant["baseline"]
    assert baseline.turns == ["Rewrite this in Swift's voice: hello world"]
    assert (tmp_path / "skills" / "ghostwrite") not in baseline.context_paths
    assert (tmp_path / "AGENTS.md") in baseline.context_paths


def test_regression_intent_emits_only_with_skill(tmp_path):
    """A case with intent=regression must produce only the with_skill plan,
    even when baseline=True is requested at the suite level."""
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        json.dumps(
            {
                "name": "ghostwrite",
                "evals": [
                    {
                        "id": "preserve-link",
                        "turns": ["hi"],
                        "intent": "regression",
                        "assertions": [{"text": "x"}],
                    }
                ],
            }
        )
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import build_run_plans, discover_suites

    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    assert plans[0].variant == "with_skill"


def test_intent_defaults_to_regression_when_omitted(tmp_path):
    """If a case omits the intent field, it defaults to regression (safer default
    — opt in to the stricter lift bar, never emit baseline accidentally)."""
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        json.dumps(
            {
                "name": "ghostwrite",
                "evals": [
                    {
                        "id": "no-intent",
                        "turns": ["hi"],
                        "assertions": [{"text": "x"}],
                    }
                ],
            }
        )
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import build_run_plans, discover_suites

    suites = discover_suites(tmp_path / "tests")
    assert suites[0].cases[0].intent == "regression"
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    assert plans[0].variant == "with_skill"


def test_build_run_plans_skill_no_baseline(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import build_run_plans, discover_suites

    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=False)
    assert len(plans) == 1
    assert plans[0].variant == "with_skill"


def test_build_run_plans_core(tmp_path):
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )
    (tmp_path / "AGENTS.md").write_text("# project context")

    from tests.support.harness.discovery import build_run_plans, discover_suites

    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    plan = plans[0]
    assert plan.variant == "run"
    assert plan.suite_name == "no-ai-attribution"
    assert plan.case_id == "throwaway-commit"
    assert (tmp_path / "AGENTS.md") in plan.context_paths


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
                        "assertions": [{"text": "x", "tool_called": "y"}],
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
