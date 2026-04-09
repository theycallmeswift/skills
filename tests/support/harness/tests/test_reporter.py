import io
from contextlib import redirect_stdout
from pathlib import Path

from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.reporter import CaseResult, DotsReporter, _print_summary
from tests.support.harness.runner import RunResult


def _cr(suite, case_id, kind, tier, passed, total, variant="run"):
    return CaseResult(
        plan=RunPlan(
            suite_name=suite,
            suite_kind=kind,
            case_id=case_id,
            variant=variant,
            turns=["hi"],
            context_paths=[],
            case=EvalCase(id=case_id, turns=["hi"]),
            tier=tier,
        ),
        run=RunResult(
            stdout="",
            files_written={},
            input_tokens=0,
            output_tokens=0,
            duration_s=1.0,
            exit_code=0,
            tool_trace=[],
            turn_count=1,
        ),
        grading=Grading.from_expectations(
            [{"text": f"c{i}", "passed": i < passed, "evidence": ""} for i in range(total)]
        ),
    )


def test_fast_tier_summary_single_table_no_warn():
    results = [
        _cr("ghostwrite", "sponsor-email", "skill", "test", passed=4, total=4),
        _cr("ghostwrite", "linkedin", "skill", "test", passed=3, total=4),
        _cr("skill-triggers", "t1", "core", "test", passed=3, total=3),
    ]
    buf = io.StringIO()
    with redirect_stdout(buf):
        _print_summary(results, verbose=False, model="claude-haiku-4-5")
    out = buf.getvalue()
    assert "WARN" not in out
    assert "baseline" not in out
    assert "## Core" in out
    assert "## Skills" in out
    assert "claude-haiku-4-5" in out
    assert "ghostwrite" in out


def _mk_result(suite, case_id, variant, kind, passed, failed, exit_code=0, intent="regression"):
    case = EvalCase(id=case_id, turns=["x"], assertions=[], intent=intent)
    plan = RunPlan(
        suite_name=suite,
        suite_kind=kind,
        case_id=case_id,
        variant=variant,
        turns=["x"],
        context_paths=[],
        case=case,
        tier="eval",
    )
    run = RunResult(
        stdout="",
        files_written={},
        input_tokens=10,
        output_tokens=10,
        duration_s=1.0,
        exit_code=exit_code,
    )
    grading = Grading.from_expectations(
        [{"text": "x", "passed": True, "evidence": "y"}] * passed
        + [{"text": "x", "passed": False, "evidence": "y"}] * failed
    )
    return CaseResult(plan=plan, run=run, grading=grading)


def test_dots_reporter_summary_skill_pass(capsys):
    r = DotsReporter()
    r.start(2)
    results = [
        _mk_result("ghostwrite", "sponsor-email", "with_skill", "skill", passed=3, failed=0),
        _mk_result("ghostwrite", "sponsor-email", "baseline", "skill", passed=1, failed=2),
    ]
    for res in results:
        r.case_finished(res)
    exit_code = r.finish(results, verbose=False)
    out = capsys.readouterr().out
    assert ".." in out
    assert "## Skills (regression)" in out
    assert "ghostwrite" in out
    assert exit_code == 0  # baseline failures don't break exit code


def test_dots_reporter_exit_code_on_with_skill_fail(capsys):
    r = DotsReporter()
    r.start(1)
    results = [_mk_result("ghostwrite", "sponsor-email", "with_skill", "skill", passed=1, failed=1)]
    for res in results:
        r.case_finished(res)
    exit_code = r.finish(results, verbose=False)
    assert exit_code == 1


def _make_result(
    variant="with_skill",
    suite_kind="skill",
    passed=1,
    failed=0,
    exit_code=0,
    intent="regression",
):
    case = EvalCase(id="c1", turns=["hi"], intent=intent)
    plan = RunPlan(
        suite_name="demo",
        suite_kind=suite_kind,
        case_id="c1",
        variant=variant,
        turns=["hi"],
        context_paths=[],
        case=case,
        tier="eval",
    )
    run = RunResult(
        stdout="",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=exit_code,
        tool_trace=[],
        turn_count=1,
    )
    exps = [{"text": f"e{i}", "passed": True, "evidence": "ok"} for i in range(passed)]
    exps += [{"text": f"f{i}", "passed": False, "evidence": "no"} for i in range(failed)]
    return CaseResult(plan=plan, run=run, grading=Grading.from_expectations(exps))


def test_all_pass_returns_0(capsys):
    assert _print_summary([_make_result(passed=3)], verbose=False) == 0


def test_failed_assertion_returns_1(capsys):
    assert _print_summary([_make_result(passed=1, failed=1)], verbose=False) == 1


def test_run_error_returns_1(capsys):
    assert _print_summary([_make_result(exit_code=1)], verbose=False) == 1


def test_baseline_failure_does_not_fail_run(capsys):
    assert (
        _print_summary(
            [_make_result(variant="baseline", passed=0, failed=3)],
            verbose=False,
        )
        == 0
    )


def test_regression_intent_fails_on_any_failure(capsys):
    """Regression cases must hit 100% or the suite fails."""
    ws = _make_result(variant="with_skill", intent="regression", passed=3, failed=1)
    exit_code = _print_summary([ws], verbose=False)
    out = capsys.readouterr().out
    assert "## Skills (regression)" in out
    assert "fail" in out
    assert exit_code == 1


def test_core_failure_returns_1(capsys):
    assert (
        _print_summary(
            [_make_result(suite_kind="core", variant="run", failed=1)],
            verbose=False,
        )
        == 1
    )


def test_deep_tier_summary_has_three_tables_and_no_warn():
    # Build a result set with one core, one regression, one lift (with baseline).
    results = [
        _cr("skill-triggers", "t1", "core", "eval", passed=3, total=3),
        _cr("summarize", "paste-raw-text", "skill", "eval", passed=4, total=4, variant="with_skill"),
        _cr(
            "ghostwrite", "sponsor-email", "skill", "eval", passed=4, total=4, variant="with_skill"
        ),
        _cr(
            "ghostwrite", "sponsor-email", "skill", "eval", passed=2, total=4, variant="baseline"
        ),
    ]
    # Mark ghostwrite sponsor-email as lift intent:
    results[2].plan.case.intent = "lift"
    results[3].plan.case.intent = "lift"
    # summarize paste-raw-text is regression by default.

    buf = io.StringIO()
    with redirect_stdout(buf):
        _print_summary(results, verbose=False, model="claude-sonnet-4-6")
    out = buf.getvalue()
    assert "## Core" in out
    assert "## Skills (regression)" in out
    assert "## Lift" in out
    assert "WARN" not in out
    assert "claude-sonnet-4-6" in out
