from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OptimizationResult:
    """Result returned by any optimization strategy."""

    prompt: str
    metadata: dict = field(default_factory=dict)


class Strategy(Protocol):
    """Protocol that all optimization strategies must implement."""

    name: str

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult: ...


def _build_registry() -> dict[str, type[Strategy]]:
    from src.optimizers.bootstrap_fewshot import BootstrapFewShotStrategy
    from src.optimizers.gepa import GEPAStrategy

    return {
        "bootstrap_fewshot": BootstrapFewShotStrategy,
        "gepa": GEPAStrategy,
    }


STRATEGIES: dict[str, type[Strategy]] = {}


def get_strategy(name: str) -> type[Strategy]:
    """Look up a strategy by name. Raises ValueError if not found."""
    if not STRATEGIES:
        STRATEGIES.update(_build_registry())
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]
