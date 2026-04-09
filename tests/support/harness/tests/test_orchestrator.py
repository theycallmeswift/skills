import asyncio
import json
from pathlib import Path

import pytest

from tests.support.harness import orchestrator
from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.orchestrator import _should_rubric_grade
from tests.support.harness.reporter import DotsReporter
from tests.support.harness.runner import RunResult


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "tests").mkdir(parents=True)
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo" / "SKILL.md").write_text("demo skill")
    (root / "references" / "specs").mkdir(parents=True)
    (root / "AGENTS.md").write_text("agents")
    (root / "tests" / "demo.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "evals": [
                    {
                        "id": "happy",
                        "turns": ["do the thing"],
                        "assertions": [{"contains": "hello"}],
                        "cleanup": ["references/specs/demo-*.md"],
                    },
                ],
            }
        )
    )
    # Seed a spec file that the cleanup glob should remove after the run.
    (root / "references" / "specs" / "demo-artifact.md").write_text("stale")
    return root


@pytest.fixture
def fake_run_and_grade(monkeypatch):
    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        return RunResult(
            stdout="hello world",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
        )

    def fake_grade(run, assertions):
        exps = [{"text": str(a), "passed": True, "evidence": "ok"} for a in assertions]
        return Grading.from_expectations(exps)

    monkeypatch.setattr(orchestrator, "run_claude", fake_run_claude)
    monkeypatch.setattr(orchestrator, "grade", fake_grade)


def test_run_evals_writes_artifacts_and_honors_cleanup(tmp_path, fake_run_and_grade):
    root = _make_project(tmp_path)
    reporter = DotsReporter()

    exit_code = asyncio.run(
        orchestrator.run_evals(
            project_root=root,
            names=["demo"],
            baseline=False,
            verbose=False,
            reporter=reporter,
        )
    )

    assert exit_code == 0

    run_dirs = list((root / "tmp" / "evals").iterdir())
    assert len(run_dirs) == 1
    case_dir = run_dirs[0] / "demo" / "eval-happy" / "with_skill"
    assert (case_dir / "outputs" / "output.md").read_text() == "hello world"
    grading = json.loads((case_dir / "grading.json").read_text())
    assert grading["summary"]["passed"] == 1
    assert grading["summary"]["failed"] == 0

    assert not (root / "references" / "specs" / "demo-artifact.md").exists()


def test_run_evals_returns_1_when_assertion_fails(tmp_path, monkeypatch):
    root = _make_project(tmp_path)

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        return RunResult(
            stdout="nope",
            files_written={},
            input_tokens=0,
            output_tokens=0,
            duration_s=0.0,
            exit_code=0,
            tool_trace=[],
            turn_count=1,
        )

    def fake_grade(run, assertions):
        exps = [{"text": str(a), "passed": False, "evidence": "no"} for a in assertions]
        return Grading.from_expectations(exps)

    monkeypatch.setattr(orchestrator, "run_claude", fake_run_claude)
    monkeypatch.setattr(orchestrator, "grade", fake_grade)

    exit_code = asyncio.run(
        orchestrator.run_evals(
            project_root=root,
            names=["demo"],
            baseline=False,
            verbose=False,
            reporter=DotsReporter(),
        )
    )
    assert exit_code == 1


def _plan(tier: str, kind: str, suite_name: str) -> RunPlan:
    return RunPlan(
        suite_name=suite_name,
        suite_kind=kind,
        case_id="c1",
        variant="run",
        turns=["hi"],
        context_paths=[],
        case=EvalCase(id="c1", turns=["hi"]),
        tier=tier,
    )


def test_rubric_grading_skipped_on_fast_tier(tmp_path):
    # Even if a rubric exists, fast tier must not grade it.
    plan = _plan("test", "skill", "ghostwrite")
    assert _should_rubric_grade(plan, project_root=tmp_path) is False


def test_rubric_grading_skipped_when_no_rubric_file(tmp_path):
    plan = _plan("eval", "skill", "ghostwrite")
    # No skills/ghostwrite/RUBRIC.md on disk.
    assert _should_rubric_grade(plan, project_root=tmp_path) is False


def test_rubric_grading_runs_on_deep_tier_when_rubric_exists(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "RUBRIC.md").write_text("## Critical\n\n- x\n")
    plan = _plan("eval", "skill", "ghostwrite")
    assert _should_rubric_grade(plan, project_root=tmp_path) is True


def test_rubric_grading_skipped_for_core_suites(tmp_path):
    (tmp_path / "skills" / "skill-triggers").mkdir(parents=True)
    (tmp_path / "skills" / "skill-triggers" / "RUBRIC.md").write_text("## Critical\n\n- x\n")
    plan = _plan("eval", "core", "skill-triggers")
    assert _should_rubric_grade(plan, project_root=tmp_path) is False
