from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EvalKind = Literal["skill", "core"]
EvalIntent = Literal["lift", "regression"]


@dataclass
class EvalCase:
    id: str
    turns: list[str]
    files: list[str] = field(default_factory=list)
    assertions: list[dict] = field(default_factory=list)
    cleanup: list[str] = field(default_factory=list)
    intent: EvalIntent = "regression"


@dataclass
class EvalSuite:
    name: str
    kind: EvalKind
    source_path: Path
    cases: list[EvalCase]


RunVariant = Literal["with_skill", "baseline", "run"]
RunTier = Literal["test", "eval"]


@dataclass
class RunPlan:
    suite_name: str
    suite_kind: EvalKind
    case_id: str
    variant: RunVariant
    turns: list[str]
    context_paths: list[Path]
    case: EvalCase  # full case for grader/reporter access
    tier: RunTier = "test"


@dataclass
class Grading:
    expectations: list[dict]  # [{text, passed, evidence}]
    passed: int
    failed: int
    total: int

    @classmethod
    def from_expectations(cls, expectations: list[dict]) -> "Grading":
        passed = sum(1 for e in expectations if e.get("passed"))
        return cls(
            expectations=expectations,
            passed=passed,
            failed=len(expectations) - passed,
            total=len(expectations),
        )
