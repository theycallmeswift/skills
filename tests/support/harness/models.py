from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EvalKind = Literal["skill", "core"]

@dataclass
class EvalCase:
    id: str
    prompt: str
    files: list[str] = field(default_factory=list)
    assertions: list[dict] = field(default_factory=list)
    grader_model: str | None = None
    cleanup: list[str] = field(default_factory=list)

@dataclass
class EvalSuite:
    name: str
    kind: EvalKind
    source_path: Path
    cases: list[EvalCase]

RunVariant = Literal["with_skill", "baseline", "run"]

@dataclass
class RunPlan:
    suite_name: str
    suite_kind: EvalKind
    case_id: str
    variant: RunVariant
    prompt: str
    context_paths: list[Path]
    case: EvalCase  # full case for grader/reporter access
