import sys
from dataclasses import dataclass
from typing import Protocol
from .models import Grading, RunPlan
from .runner import RunResult

@dataclass
class CaseResult:
    plan: RunPlan
    run: RunResult
    grading: Grading

class Reporter(Protocol):
    def start(self, total: int) -> None: ...
    def case_started(self, plan: RunPlan) -> None: ...
    def case_finished(self, result: CaseResult) -> None: ...
    def finish(self, results: list[CaseResult], verbose: bool) -> int: ...

def make_reporter() -> "Reporter":
    return RichReporter() if sys.stdout.isatty() else DotsReporter()

class DotsReporter:
    def __init__(self) -> None:
        self._count = 0

    def start(self, total: int) -> None:
        print(f"Running {total} cases...")

    def case_started(self, plan: RunPlan) -> None:
        pass

    def case_finished(self, result: CaseResult) -> None:
        symbol = "."
        if result.run.exit_code != 0:
            symbol = "E"
        elif result.grading.failed > 0:
            symbol = "F"
        print(symbol, end="", flush=True)
        self._count += 1
        if self._count % 50 == 0:
            print()

    def finish(self, results: list[CaseResult], verbose: bool) -> int:
        print()
        return _print_summary(results, verbose)

def _print_summary(results: list[CaseResult], verbose: bool) -> int:
    skill_results = [r for r in results if r.plan.suite_kind == "skill"]
    core_results = [r for r in results if r.plan.suite_kind == "core"]

    exit_code = 0

    if skill_results:
        print("\n## Skill Eval Results\n")
        print(f"{'Skill':<20} {'Eval':<30} {'With Skill':<14} {'Baseline':<14} {'Delta':<8}")
        by_key: dict[tuple[str, str], dict[str, CaseResult]] = {}
        for r in skill_results:
            key = (r.plan.suite_name, r.plan.case_id)
            by_key.setdefault(key, {})[r.plan.variant] = r
        for (suite, case_id), variants in sorted(by_key.items()):
            ws = variants.get("with_skill")
            bl = variants.get("baseline")
            ws_str = _fmt_score(ws.grading) if ws else "—"
            bl_str = _fmt_score(bl.grading) if bl else "—"
            delta = ""
            if ws and bl and bl.grading.total:
                d = (ws.grading.passed / ws.grading.total) - (bl.grading.passed / bl.grading.total)
                delta = f"{d*100:+.0f}%"
            print(f"{suite:<20} {case_id:<30} {ws_str:<14} {bl_str:<14} {delta:<8}")
            if ws and ws.grading.failed > 0:
                exit_code = 1
            if ws and ws.run.exit_code != 0:
                exit_code = 1

    if core_results:
        print("\n## Core Eval Results\n")
        print(f"{'Eval':<25} {'Case':<30} {'Result':<14}")
        for r in sorted(core_results, key=lambda x: (x.plan.suite_name, x.plan.case_id)):
            print(f"{r.plan.suite_name:<25} {r.plan.case_id:<30} {_fmt_score(r.grading):<14}")
            if r.grading.failed > 0 or r.run.exit_code != 0:
                exit_code = 1

    failures: list[CaseResult] = []
    for r in results:
        if r.plan.suite_kind == "skill" and r.plan.variant == "baseline":
            continue
        if r.grading.failed > 0 or r.run.exit_code != 0:
            failures.append(r)
    if failures:
        print("\n### Failures\n")
        for r in failures:
            label = f"{r.plan.suite_name} > {r.plan.case_id} > {r.plan.variant}"
            print(f"\n**{label}**")
            if r.run.exit_code != 0:
                print(f"- RUN ERROR ({r.run.exit_code}): {r.run.error}")
            for exp in r.grading.expectations:
                if not exp["passed"]:
                    print(f"- FAIL: {exp['text']}")
                    print(f"  Evidence: {exp.get('evidence', '(none)')}")
    if verbose:
        print("\n### Passing assertions (verbose)\n")
        for r in results:
            for exp in r.grading.expectations:
                if exp["passed"]:
                    print(f"- PASS [{r.plan.suite_name}/{r.plan.case_id}]: {exp['text']}")
                    print(f"  Evidence: {exp.get('evidence', '(none)')}")

    return exit_code

def _fmt_score(g: Grading) -> str:
    if g.total == 0:
        return "n/a"
    pct = int(round(100 * g.passed / g.total))
    return f"{g.passed}/{g.total} ({pct}%)"

class RichReporter:
    def __init__(self) -> None:
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table
        self._Console = Console
        self._Live = Live
        self._Table = Table
        self._console = Console()
        self._rows: dict[tuple[str, str, str], dict] = {}
        self._live = None

    def _table(self):
        t = self._Table(title="Eval Runs")
        t.add_column("Suite")
        t.add_column("Case")
        t.add_column("Variant")
        t.add_column("Status")
        t.add_column("Duration", justify="right")
        t.add_column("Tokens", justify="right")
        t.add_column("Pass Rate", justify="right")
        for key, row in self._rows.items():
            t.add_row(*row["cells"])
        return t

    def start(self, total: int) -> None:
        self._live = self._Live(self._table(), console=self._console, refresh_per_second=4)
        self._live.__enter__()

    def case_started(self, plan: RunPlan) -> None:
        key = (plan.suite_name, plan.case_id, plan.variant)
        self._rows[key] = {"cells": [
            plan.suite_name, plan.case_id, plan.variant, "[yellow]running[/yellow]", "—", "—", "—"
        ]}
        if self._live:
            self._live.update(self._table())

    def case_finished(self, result: CaseResult) -> None:
        key = (result.plan.suite_name, result.plan.case_id, result.plan.variant)
        if result.run.exit_code != 0:
            status = "[red]error[/red]"
        elif result.grading.failed > 0:
            status = "[red]fail[/red]"
        else:
            status = "[green]pass[/green]"
        tokens = f"{result.run.input_tokens + result.run.output_tokens}"
        self._rows[key] = {"cells": [
            result.plan.suite_name,
            result.plan.case_id,
            result.plan.variant,
            status,
            f"{result.run.duration_s:.1f}s",
            tokens,
            _fmt_score(result.grading),
        ]}
        if self._live:
            self._live.update(self._table())

    def finish(self, results: list[CaseResult], verbose: bool) -> int:
        if self._live:
            self._live.__exit__(None, None, None)
            self._live = None
        return _print_summary(results, verbose)
