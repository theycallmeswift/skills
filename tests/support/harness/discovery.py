import json
from pathlib import Path
from .models import EvalCase, EvalSuite, EvalKind, RunPlan

def load_eval_file(path: Path, kind: EvalKind) -> EvalSuite:
    data = json.loads(path.read_text())
    cases = [
        EvalCase(
            id=str(c["id"]),
            prompt=c["prompt"],
            files=c.get("files", []),
            assertions=c.get("assertions", []),
            grader_model=c.get("grader_model"),
            cleanup=c.get("cleanup", []),
        )
        for c in data["evals"]
    ]
    return EvalSuite(
        name=data["name"],
        kind=kind,
        source_path=path,
        cases=cases,
    )

def discover_suites(tests_root: Path, names: list[str] | None = None) -> list[EvalSuite]:
    suites: list[EvalSuite] = []

    skills_dir = tests_root / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            evals_file = skill_dir / "evals.json"
            if evals_file.is_file():
                suites.append(load_eval_file(evals_file, kind="skill"))

    core_dir = tests_root / "core"
    if core_dir.is_dir():
        for f in sorted(core_dir.glob("*.json")):
            suites.append(load_eval_file(f, kind="core"))

    if names:
        wanted = set(names)
        suites = [s for s in suites if s.name in wanted]

    return suites

SKILL_PREAMBLE = "Before responding, read and follow skills/{name}/SKILL.md.\n\n"

def build_run_plans(
    suites: list[EvalSuite],
    project_root: Path,
    baseline: bool,
) -> list[RunPlan]:
    plans: list[RunPlan] = []
    agents_md = project_root / "AGENTS.md"

    for suite in suites:
        for case in suite.cases:
            eval_dir = suite.source_path.parent
            case_files = [eval_dir / f for f in case.files]

            if suite.kind == "skill":
                skill_dir = project_root / "skills" / suite.name
                with_skill_paths = [skill_dir, agents_md, *case_files]
                with_skill_prompt = SKILL_PREAMBLE.format(name=suite.name) + case.prompt
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="with_skill",
                    prompt=with_skill_prompt,
                    context_paths=with_skill_paths,
                    case=case,
                ))
                if baseline:
                    plans.append(RunPlan(
                        suite_name=suite.name,
                        suite_kind=suite.kind,
                        case_id=case.id,
                        variant="baseline",
                        prompt=case.prompt,
                        context_paths=[agents_md, *case_files],
                        case=case,
                    ))
            else:  # core
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="run",
                    prompt=case.prompt,
                    context_paths=[agents_md, *case_files],
                    case=case,
                ))

    return plans
