from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.reporter import CaseResult, DotsReporter, _print_summary
from tests.support.harness.runner import RunResult


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
    assert "Regression Suite" in out
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


def test_lift_intent_ok_when_with_skill_above_threshold(capsys):
    """Lift case with high with-skill rate and positive delta → OK, exit 0."""
    ws = _make_result(variant="with_skill", intent="lift", passed=4, failed=0)
    bl = _make_result(variant="baseline", intent="lift", passed=1, failed=3)
    exit_code = _print_summary([ws, bl], verbose=False)
    out = capsys.readouterr().out
    assert "Lift Suite" in out
    assert " OK" in out
    assert exit_code == 0


def test_lift_intent_warn_on_negative_delta_but_not_failing(capsys):
    """Lift case with with-skill ≥ 75% but delta ≤ 0 → WARN, exit 0.
    Per Option 2: zero/negative delta is informational, not a failure."""
    ws = _make_result(variant="with_skill", intent="lift", passed=4, failed=0)
    bl = _make_result(variant="baseline", intent="lift", passed=4, failed=0)
    exit_code = _print_summary([ws, bl], verbose=False)
    out = capsys.readouterr().out
    assert "Lift Suite" in out
    # Equal rates → delta 0 → neither negative nor positive; status should be OK.
    # (Warn is only for strictly negative deltas.)
    assert exit_code == 0


def test_lift_intent_fails_when_with_skill_below_threshold(capsys):
    """Lift case with with-skill < 75% → FAIL, exit 1."""
    ws = _make_result(variant="with_skill", intent="lift", passed=2, failed=4)
    bl = _make_result(variant="baseline", intent="lift", passed=0, failed=6)
    exit_code = _print_summary([ws, bl], verbose=False)
    assert exit_code == 1


def test_lift_intent_strictly_negative_delta_emits_warn(capsys):
    """Lift case with positive with-skill rate but strictly negative delta
    (baseline > with-skill) → WARN, not FAIL (exit 0)."""
    ws = _make_result(variant="with_skill", intent="lift", passed=3, failed=1)
    bl = _make_result(variant="baseline", intent="lift", passed=4, failed=0)
    exit_code = _print_summary([ws, bl], verbose=False)
    out = capsys.readouterr().out
    assert "WARN" in out
    assert exit_code == 0


def test_regression_intent_fails_on_any_failure(capsys):
    """Regression cases must hit 100% or the suite fails."""
    ws = _make_result(variant="with_skill", intent="regression", passed=3, failed=1)
    exit_code = _print_summary([ws], verbose=False)
    out = capsys.readouterr().out
    assert "Regression Suite" in out
    assert "FAIL" in out
    assert exit_code == 1


def test_core_failure_returns_1(capsys):
    assert (
        _print_summary(
            [_make_result(suite_kind="core", variant="run", failed=1)],
            verbose=False,
        )
        == 1
    )
