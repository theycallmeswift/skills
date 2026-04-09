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
    def finish(self, results: list[CaseResult], verbose: bool, model: str | None = None) -> int: ...


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

    def finish(self, results: list[CaseResult], verbose: bool, model: str | None = None) -> int:
        print()
        return _print_summary(results, verbose, model=model)


def _print_summary(results: list[CaseResult], verbose: bool, model: str | None = None) -> int:
    if not results:
        return 0
    tier = results[0].plan.tier
    if tier == "test":
        return _print_fast_summary(results, verbose=verbose, model=model)
    return _print_deep_summary(results, verbose=verbose, model=model)


def _print_deep_summary(results: list[CaseResult], verbose: bool, model: str | None) -> int:
    exit_code = 0
    model_label = model or "default"

    core = [r for r in results if r.plan.suite_kind == "core"]
    skill = [r for r in results if r.plan.suite_kind == "skill"]

    # Core table
    if core:
        print(f"\n## Core — {model_label}\n")
        by_suite: dict[str, list[CaseResult]] = {}
        for r in core:
            by_suite.setdefault(r.plan.suite_name, []).append(r)
        for suite, cases in sorted(by_suite.items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<32} {passed}/{total} checks   {status}")

    # Pair up with_skill and baseline runs by (suite, case_id)
    by_key: dict[tuple[str, str], dict[str, CaseResult]] = {}
    for r in skill:
        by_key.setdefault((r.plan.suite_name, r.plan.case_id), {})[r.plan.variant] = r

    regression_rows = []
    lift_rows = []
    for (suite, case_id), variants in sorted(by_key.items()):
        ws = variants.get("with_skill")
        if ws is None:
            continue
        if ws.plan.case.intent == "lift":
            lift_rows.append((suite, case_id, ws, variants.get("baseline")))
        else:
            regression_rows.append((suite, case_id, ws))

    if regression_rows:
        print(f"\n## Skills (regression) — {model_label}\n")
        for suite, case_id, ws in regression_rows:
            failing = ws.run.exit_code != 0 or ws.grading.failed > 0
            if failing:
                exit_code = 1
            status = "fail" if failing else "ok"
            print(f"{suite:<20} {case_id:<32} {_fmt_score(ws.grading):<14} {status}")

    if lift_rows:
        print(f"\n## Lift — {model_label}\n")
        for suite, case_id, ws, bl in lift_rows:
            ws_str = _fmt_score(ws.grading)
            bl_str = _fmt_score(bl.grading) if bl else "—"
            failing = ws.run.exit_code != 0 or ws.grading.failed > 0
            if failing:
                exit_code = 1
            status = "fail" if failing else "ok"
            print(
                f"{suite:<20} {case_id:<32} with_skill={ws_str:<12} baseline={bl_str:<12} {status}"
            )

    _print_failures(results, verbose)
    return exit_code


def _print_fast_summary(results: list[CaseResult], verbose: bool, model: str | None) -> int:
    exit_code = 0
    by_suite_kind: dict[str, dict[str, list[CaseResult]]] = {"core": {}, "skill": {}}
    for r in results:
        suite = r.plan.suite_name
        by_suite_kind[r.plan.suite_kind].setdefault(suite, []).append(r)

    if by_suite_kind["core"]:
        print("\n## Core\n")
        for suite, cases in sorted(by_suite_kind["core"].items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<25} {passed}/{total}  {status}")

    if by_suite_kind["skill"]:
        print("\n## Skills\n")
        for suite, cases in sorted(by_suite_kind["skill"].items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<25} {passed}/{total}  {status}")

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.grading.failed == 0 and r.run.exit_code == 0)
    pct = int(round(100 * passed_cases / total_cases)) if total_cases else 0
    print(f"\n{passed_cases}/{total_cases} pass ({pct}%) on {model or 'default'}")
    _print_failures(results, verbose)
    return exit_code


def _print_failures(results: list[CaseResult], verbose: bool) -> None:
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
        for _key, row in self._rows.items():
            t.add_row(*row["cells"])
        return t

    def start(self, total: int) -> None:
        self._live = self._Live(self._table(), console=self._console, refresh_per_second=4)
        self._live.__enter__()

    def case_started(self, plan: RunPlan) -> None:
        key = (plan.suite_name, plan.case_id, plan.variant)
        self._rows[key] = {
            "cells": [
                plan.suite_name,
                plan.case_id,
                plan.variant,
                "[yellow]running[/yellow]",
                "—",
                "—",
                "—",
            ]
        }
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
        self._rows[key] = {
            "cells": [
                result.plan.suite_name,
                result.plan.case_id,
                result.plan.variant,
                status,
                f"{result.run.duration_s:.1f}s",
                tokens,
                _fmt_score(result.grading),
            ]
        }
        if self._live:
            self._live.update(self._table())

    def finish(self, results: list[CaseResult], verbose: bool, model: str | None = None) -> int:
        if self._live:
            self._live.__exit__(None, None, None)
            self._live = None
        return _print_summary(results, verbose, model=model)
