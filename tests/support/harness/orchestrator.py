import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .discovery import discover_suites, build_run_plans
from .grader import grade
from .models import RunPlan
from .reporter import CaseResult, Reporter
from .runner import run_claude

CONCURRENCY = 4

def _artifact_dir(root: Path, plan: RunPlan, run_id: str) -> Path:
    if plan.suite_kind == "core":
        base = root / run_id / "_core" / plan.suite_name / f"eval-{plan.case_id}" / "run"
    else:
        base = root / run_id / plan.suite_name / f"eval-{plan.case_id}" / plan.variant
    base.mkdir(parents=True, exist_ok=True)
    return base

async def _run_one(
    plan: RunPlan,
    project_root: Path,
    artifact_root: Path,
    run_id: str,
    reporter: Reporter,
    sem: asyncio.Semaphore,
) -> CaseResult:
    async with sem:
        reporter.case_started(plan)
        with tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
            cwd = Path(tmp)
            run = await run_claude(
                turns=plan.turns,
                cwd=cwd,
                context_paths=plan.context_paths,
                project_root=project_root,
            )

            original_prompt = "\n\n".join(
                f"[turn {i}] {t}" for i, t in enumerate(plan.case.turns, start=1)
            )
            grading = await grade(
                run,
                plan.case.assertions,
                model=plan.case.grader_model,
                original_prompt=original_prompt,
            )

            adir = _artifact_dir(artifact_root, plan, run_id)
            (adir / "outputs").mkdir(exist_ok=True)
            (adir / "outputs" / "output.md").write_text(run.stdout)
            (adir / "files_written.json").write_text(
                json.dumps(run.files_written, indent=2)
            )
            (adir.parent / "eval_metadata.json").write_text(json.dumps({
                "id": plan.case_id,
                "turns": plan.case.turns,
                "turn_count": len(plan.case.turns),
                "assertions": plan.case.assertions,
            }, indent=2))
            (adir / "grading.json").write_text(json.dumps({
                "expectations": grading.expectations,
                "summary": {
                    "passed": grading.passed,
                    "failed": grading.failed,
                    "total": grading.total,
                    "pass_rate": (grading.passed / grading.total) if grading.total else 0.0,
                },
            }, indent=2))

            result = CaseResult(plan=plan, run=run, grading=grading)

        # Post-run cleanup: safe globs only (validated at discovery time).
        for pattern in plan.case.cleanup:
            for match in project_root.glob(pattern):
                if match.is_dir():
                    shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

        reporter.case_finished(result)
        return result

async def run_evals(
    project_root: Path,
    names: list[str] | None,
    baseline: bool,
    verbose: bool,
    reporter: Reporter,
) -> int:
    tests_root = project_root / "tests"
    suites = discover_suites(tests_root, names=names)
    if not suites:
        print(f"No eval suites found under {tests_root}")
        return 1

    plans = build_run_plans(suites, project_root=project_root, baseline=baseline)
    artifact_root = project_root / "tmp" / "evals"
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    reporter.start(len(plans))
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [_run_one(p, project_root, artifact_root, run_id, reporter, sem) for p in plans]
    results = await asyncio.gather(*tasks)
    exit_code = reporter.finish(list(results), verbose=verbose)
    print(f"\nFull results: tmp/evals/{run_id}/")
    return exit_code
