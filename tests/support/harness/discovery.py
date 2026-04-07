import json
from pathlib import Path
from .models import EvalCase, EvalSuite, EvalKind

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
