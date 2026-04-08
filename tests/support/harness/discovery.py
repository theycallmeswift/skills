import json
from pathlib import Path
from .models import EvalCase, EvalSuite, EvalKind, RunPlan

_CLEANUP_ALLOWED_ROOTS = ("references/specs/", "tmp/")


def _validate_cleanup(patterns: list[str], source: Path) -> list[str]:
    """Reject cleanup globs that could touch files outside the safe allowlist.

    Patterns must be relative, contain no `..` segments, and start with one of
    the allowed roots. This runs at load time so bad configs fail loudly.
    """
    if not isinstance(patterns, list):
        raise ValueError(
            f"eval case in {source}: 'cleanup' must be a list of glob strings."
        )
    for p in patterns:
        if not isinstance(p, str) or not p:
            raise ValueError(
                f"eval case in {source}: cleanup entries must be non-empty strings."
            )
        if p.startswith("/"):
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' is absolute; "
                f"use a path relative to project_root."
            )
        if ".." in Path(p).parts:
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' contains '..'; "
                f"parent traversal is not allowed."
            )
        if not any(p.startswith(root) for root in _CLEANUP_ALLOWED_ROOTS):
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' is not under "
                f"allowed roots {_CLEANUP_ALLOWED_ROOTS}."
            )
    return patterns


def _load_turns(case: dict, source: Path) -> list[str]:
    turns = case.get("turns")
    if turns is None:
        raise ValueError(
            f"eval case '{case.get('id', '?')}' in {source} is missing 'turns'. "
            f"Use a list of strings, e.g. \"turns\": [\"first message\"]."
        )
    if not isinstance(turns, list) or not turns or not all(isinstance(t, str) for t in turns):
        raise ValueError(
            f"eval case '{case.get('id', '?')}' in {source}: 'turns' must be a non-empty list of strings."
        )
    return turns


def load_eval_file(path: Path, kind: EvalKind) -> EvalSuite:
    data = json.loads(path.read_text())
    shared = data.get("shared_assertions", [])
    if not isinstance(shared, list):
        raise ValueError(
            f"{path}: 'shared_assertions' must be a list of assertion dicts."
        )

    cases: list[EvalCase] = []
    for c in data["evals"]:
        own = c.get("assertions", [])
        if c.get("use_shared_assertions", True):
            merged = [*shared, *own]
        else:
            merged = list(own)
        cases.append(EvalCase(
            id=str(c["id"]),
            turns=_load_turns(c, path),
            files=c.get("files", []),
            assertions=merged,
            grader_model=c.get("grader_model"),
            cleanup=_validate_cleanup(c.get("cleanup", []), path),
        ))
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


def _with_preamble(turns: list[str], suite_name: str) -> list[str]:
    preamble = SKILL_PREAMBLE.format(name=suite_name)
    return [preamble + turns[0], *turns[1:]]


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
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="with_skill",
                    turns=_with_preamble(case.turns, suite.name),
                    context_paths=with_skill_paths,
                    case=case,
                ))
                if baseline:
                    plans.append(RunPlan(
                        suite_name=suite.name,
                        suite_kind=suite.kind,
                        case_id=case.id,
                        variant="baseline",
                        turns=list(case.turns),
                        context_paths=[agents_md, *case_files],
                        case=case,
                    ))
            else:  # core
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="run",
                    turns=list(case.turns),
                    context_paths=[agents_md, *case_files],
                    case=case,
                ))

    return plans
