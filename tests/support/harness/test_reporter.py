from pathlib import Path
from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.runner import RunResult
from tests.support.harness.reporter import DotsReporter, CaseResult

def _mk_result(suite, case_id, variant, kind, passed, failed, exit_code=0):
    case = EvalCase(id=case_id, prompt="x", assertions=[])
    plan = RunPlan(
        suite_name=suite, suite_kind=kind, case_id=case_id, variant=variant,
        prompt="x", context_paths=[], case=case,
    )
    run = RunResult(stdout="", files_written={}, input_tokens=10, output_tokens=10, duration_s=1.0, exit_code=exit_code)
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
    assert "Skill Eval Results" in out
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
