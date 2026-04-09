import asyncio

import pytest

from tests.support.harness.grader import (
    _grade_deterministic,
    _resolve_source,
    _truncate_tail,
    grade,
    grade_rubric,
)
from tests.support.harness.models import Grading
from tests.support.harness.runner import RunResult


def _run(stdout="", final_message="", files_written=None):
    return RunResult(
        stdout=stdout,
        files_written=files_written or {},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=0,
        tool_trace=[],
        turn_count=1,
        final_message=final_message,
    )


def test_resolve_source_defaults_to_final_message():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, None) == ["FINAL"]


def test_resolve_source_stdout():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, "stdout") == ["STDOUT"]


def test_resolve_source_final_message_explicit():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, "final_message") == ["FINAL"]


def test_resolve_source_files_glob_returns_all_matches():
    run = _run(files_written={"a.md": "alpha", "b.md": "beta", "c.txt": "gamma"})
    got = _resolve_source(run, "files.*.md")
    assert sorted(got) == ["alpha", "beta"]


def test_resolve_source_files_glob_no_matches_returns_empty():
    run = _run(files_written={"a.md": "alpha"})
    assert _resolve_source(run, "files.*.txt") == []


def test_truncate_tail_keeps_end_and_adds_marker():
    s = "a" * 100
    out = _truncate_tail(s, limit=30)
    assert out.endswith("a" * 30)
    assert "truncated" in out
    assert "70" in out


def test_truncate_tail_noop_when_under_limit():
    s = "short"
    assert _truncate_tail(s, limit=100) == "short"



def _run_with_trace(trace):
    return RunResult(
        stdout="",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=0,
        tool_trace=trace,
        turn_count=1,
    )


def test_tool_called_passes_when_name_matches_substring():
    run = _run_with_trace([{"name": "mcp__brightdata__scrape_as_markdown", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "scrape_as_markdown"}], run)
    assert exps == [
        {
            "text": "tool_called: scrape_as_markdown",
            "passed": True,
            "evidence": "matched tool 'mcp__brightdata__scrape_as_markdown' on turn 1",
        }
    ]


def test_tool_called_fails_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "no matching tool" in exps[0]["evidence"].lower()


def test_tool_not_called_passes_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is True


def test_tool_not_called_fails_when_present():
    run = _run_with_trace([{"name": "WebFetch", "input": {"url": "x"}, "turn": 2}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "turn 2" in exps[0]["evidence"]


def test_skill_invoked_matches_bare_name():
    run = _run_with_trace(
        [
            {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1},
        ]
    )
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_matches_prefixed_name():
    run = _run_with_trace(
        [
            {"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 1},
        ]
    )
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_fails_when_different_skill():
    run = _run_with_trace(
        [
            {"name": "Skill", "input": {"skill": "summarize"}, "turn": 1},
        ]
    )
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False


def test_skill_invoked_fails_when_no_skill_tool_at_all():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "no Skill tool" in exps[0]["evidence"]


def test_skill_not_invoked_passes_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_not_invoked_fails_when_skill_fired():
    run = _run_with_trace(
        [{"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}]
    )
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "ghostwrite" in exps[0]["evidence"]


def test_skill_not_invoked_accepts_prefixed_name():
    run = _run_with_trace(
        [{"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 2}]
    )
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False



def test_regex_passes_on_single_match():
    run = _run(final_message="Hey, Sarah -- welcome")
    exps = _grade_deterministic([{"regex": r"^Hey, Sarah --"}], run)
    assert exps[0]["passed"] is True
    assert exps[0]["text"].startswith("regex:")


def test_regex_fails_when_absent():
    run = _run(final_message="Hello world")
    exps = _grade_deterministic([{"regex": r"^Hey"}], run)
    assert exps[0]["passed"] is False


def test_regex_min_count_enforced():
    run = _run(final_message="one? two?")
    exps = _grade_deterministic([{"regex": r"\?", "min": 3}], run)
    assert exps[0]["passed"] is False
    assert "2" in exps[0]["evidence"]


def test_regex_max_count_enforced():
    run = _run(final_message="one? two? three?")
    exps = _grade_deterministic([{"regex": r"\?", "max": 2}], run)
    assert exps[0]["passed"] is False


def test_regex_min_and_max_inclusive():
    run = _run(final_message="a? b?")
    exps = _grade_deterministic([{"regex": r"\?", "min": 2, "max": 2}], run)
    assert exps[0]["passed"] is True


def test_regex_respects_on_field_stdout():
    run = _run(stdout="VISIBLE", final_message="HIDDEN")
    exps = _grade_deterministic(
        [{"regex": "VISIBLE", "on": "stdout"}], run
    )
    assert exps[0]["passed"] is True


def test_not_regex_passes_when_absent():
    run = _run(final_message="clean output")
    exps = _grade_deterministic([{"not_regex": "forbidden"}], run)
    assert exps[0]["passed"] is True


def test_not_regex_fails_when_present():
    run = _run(final_message="forbidden word here")
    exps = _grade_deterministic([{"not_regex": "forbidden"}], run)
    assert exps[0]["passed"] is False


def test_contains_literal_substring_passes():
    run = _run(final_message="the answer is 42")
    exps = _grade_deterministic([{"contains": "42"}], run)
    assert exps[0]["passed"] is True


def test_contains_fails_when_absent():
    run = _run(final_message="hello")
    exps = _grade_deterministic([{"contains": "world"}], run)
    assert exps[0]["passed"] is False


def test_contains_all_requires_every_literal():
    run = _run(final_message="450 fellows, 30% up, 92% rec rate")
    exps = _grade_deterministic(
        [{"contains_all": ["450", "30%", "92%"]}], run
    )
    assert exps[0]["passed"] is True


def test_contains_all_fails_on_missing_item():
    run = _run(final_message="450 fellows, 30% up")
    exps = _grade_deterministic(
        [{"contains_all": ["450", "30%", "92%"]}], run
    )
    assert exps[0]["passed"] is False
    assert "92%" in exps[0]["evidence"]


def test_not_contains_passes_when_absent():
    run = _run(final_message="clean")
    exps = _grade_deterministic([{"not_contains": "dirty"}], run)
    assert exps[0]["passed"] is True


def test_not_contains_fails_when_present():
    run = _run(final_message="dirty string")
    exps = _grade_deterministic([{"not_contains": "dirty"}], run)
    assert exps[0]["passed"] is False



def test_script_name_runs_skill_lint_and_passes_on_clean():
    clean = "Hey, Sarah,\n\nSeason 3 wrapped with 450 fellows.\n\n- Swift\n"
    run = _run(final_message=clean)
    exps = _grade_deterministic([{"script_name": "ghostwrite"}], run)
    assert len(exps) == 1
    assert exps[0]["passed"] is True
    assert exps[0]["text"] == "script_name: ghostwrite"


def test_script_name_fails_on_em_dash():
    run = _run(final_message="We shipped it — finally.\n")
    exps = _grade_deterministic([{"script_name": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "em dash" in exps[0]["evidence"]



def test_output_len_lte_passes_under_bound():
    run = _run(final_message="short")
    exps = _grade_deterministic([{"output_len_lte": 100}], run)
    assert exps[0]["passed"] is True


def test_output_len_lte_fails_over_bound():
    run = _run(final_message="x" * 200)
    exps = _grade_deterministic([{"output_len_lte": 100}], run)
    assert exps[0]["passed"] is False
    assert "200" in exps[0]["evidence"]


def test_output_len_gte_enforces_minimum():
    run = _run(final_message="short")
    exps = _grade_deterministic([{"output_len_gte": 100}], run)
    assert exps[0]["passed"] is False


def test_output_len_respects_on_stdout():
    run = _run(stdout="x" * 50, final_message="")
    exps = _grade_deterministic(
        [{"output_len_lte": 40, "on": "stdout"}], run
    )
    assert exps[0]["passed"] is False


def test_token_usage_lte_passes():
    run = _run()
    run.input_tokens = 1000
    run.output_tokens = 500
    exps = _grade_deterministic([{"token_usage_lte": 2000}], run)
    assert exps[0]["passed"] is True


def test_token_usage_lte_fails_over_cap():
    run = _run()
    run.input_tokens = 5000
    run.output_tokens = 6000
    exps = _grade_deterministic([{"token_usage_lte": 10000}], run)
    assert exps[0]["passed"] is False
    assert "11000" in exps[0]["evidence"]


def test_trace_order_passes_when_tools_in_order():
    trace = [
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
        {"name": "Bash", "input": {}, "turn": 1},
        {"name": "Write", "input": {}, "turn": 1},
    ]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is True


def test_trace_order_fails_when_out_of_order():
    trace = [
        {"name": "Write", "input": {}, "turn": 1},
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
    ]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is False


def test_trace_order_fails_when_missing_tool():
    trace = [{"name": "scrape_as_markdown", "input": {}, "turn": 1}]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is False
    assert "Write" in exps[0]["evidence"]


def test_trace_count_lte_passes_under_cap():
    run = _run_with_trace(
        [{"name": "Bash", "input": {}, "turn": 1} for _ in range(2)]
    )
    exps = _grade_deterministic(
        [{"trace_count_lte": {"tool": "Bash", "n": 3}}], run
    )
    assert exps[0]["passed"] is True


def test_trace_count_lte_fails_over_cap():
    run = _run_with_trace(
        [{"name": "Bash", "input": {}, "turn": 1} for _ in range(5)]
    )
    exps = _grade_deterministic(
        [{"trace_count_lte": {"tool": "Bash", "n": 3}}], run
    )
    assert exps[0]["passed"] is False
    assert "5" in exps[0]["evidence"]


def test_turn_count_lte_passes():
    run = _run_with_trace([])
    run.turn_count = 1
    exps = _grade_deterministic([{"turn_count_lte": 1}], run)
    assert exps[0]["passed"] is True


def test_turn_count_lte_fails():
    run = _run_with_trace([])
    run.turn_count = 3
    exps = _grade_deterministic([{"turn_count_lte": 1}], run)
    assert exps[0]["passed"] is False


def test_files_written_include_passes_on_match():
    run = _run(files_written={"references/specs/foo.md": "x"})
    exps = _grade_deterministic(
        [{"files_written_include": "references/specs/*.md"}], run
    )
    assert exps[0]["passed"] is True


def test_files_written_include_fails_when_nothing_matches():
    run = _run(files_written={"other.txt": "x"})
    exps = _grade_deterministic(
        [{"files_written_include": "references/specs/*.md"}], run
    )
    assert exps[0]["passed"] is False


def test_files_written_exclude_passes_when_no_match():
    run = _run(files_written={"notes.md": "x"})
    exps = _grade_deterministic(
        [{"files_written_exclude": "package.json"}], run
    )
    assert exps[0]["passed"] is True


def test_files_written_exclude_fails_on_match():
    run = _run(files_written={"package.json": "{}"})
    exps = _grade_deterministic(
        [{"files_written_exclude": "package.json"}], run
    )
    assert exps[0]["passed"] is False


def test_files_written_count_zero_passes_when_no_files():
    run = _run(files_written={})
    exps = _grade_deterministic([{"files_written_count": 0}], run)
    assert exps[0]["passed"] is True


def test_files_written_count_zero_fails_when_files_exist():
    run = _run(files_written={"a.md": "x", "sub/b.md": "y"})
    exps = _grade_deterministic([{"files_written_count": 0}], run)
    assert exps[0]["passed"] is False
    assert "2" in exps[0]["evidence"]


def test_files_written_count_exact_match():
    run = _run(files_written={"a.md": "x", "b.md": "y"})
    exps = _grade_deterministic([{"files_written_count": 2}], run)
    assert exps[0]["passed"] is True


def test_file_contains_text_literal_passes():
    run = _run(files_written={"references/specs/foo.md": "Out of scope: X"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "references/specs/*.md", "text": "Out of scope"}}],
        run,
    )
    assert exps[0]["passed"] is True


def test_file_contains_text_fails_when_no_matching_file():
    run = _run(files_written={"other.txt": "irrelevant"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "x"}}], run
    )
    assert exps[0]["passed"] is False
    assert "no files matched" in exps[0]["evidence"]


def test_file_contains_text_fails_when_text_absent():
    run = _run(files_written={"a.md": "no match here"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "needed"}}], run
    )
    assert exps[0]["passed"] is False


def test_file_contains_regex_passes():
    run = _run(files_written={"a.md": "allowlist entry"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "regex": r"(?i)(allowlist|routing)"}}], run
    )
    assert exps[0]["passed"] is True


def test_file_contains_requires_exactly_one_of_text_or_regex():
    run = _run(files_written={"a.md": "x"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "x", "regex": "x"}}], run
    )
    assert exps[0]["passed"] is False
    assert "exactly one" in exps[0]["evidence"]


def test_grade_rubric_returns_empty_when_no_items(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("# no items\n")
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert isinstance(result, Grading)
    assert result.total == 0


def test_grade_rubric_passes_when_all_critical_pass(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n- item B\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "item A", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "item B", "critical": True, "status": "pass", "evidence": "ok"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert result.passed == 2
    assert result.failed == 0


def test_grade_rubric_fails_when_critical_item_fails(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n")

    async def fake_llm_call(prompt, model):
        return {"items": [{"text": "item A", "critical": True, "status": "fail", "evidence": "missing"}]}

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert result.failed == 1


def test_grade_rubric_na_counts_as_pass_for_critical_gate(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n- item B\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "item A", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "item B", "critical": True, "status": "n/a", "evidence": "not applicable"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    # Case passes: both critical items are pass/na. We report n/a items as
    # "passed" for aggregate scoring simplicity — the rubric summary on screen
    # can show na breakdowns separately.
    assert result.failed == 0
    assert result.total == 2


def test_grade_rubric_optional_failures_dont_fail_the_case(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- crit\n\n## Optional\n\n- opt\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "crit", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "opt", "critical": False, "status": "fail", "evidence": "nope"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    # Optional fail is reported but doesn't count toward `failed`.
    assert result.failed == 0
    assert result.total == 2
