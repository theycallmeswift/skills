"""Pytest plugin for eval result reporting.

Registered via conftest.py: pytest_plugins = ["tests.support.harness.reporter"]
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath


class EvalReporter:
    """Collects test results and formats a summary table."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._results: dict[str, list] = defaultdict(list)
        self._durations: dict[str, float] = defaultdict(float)

    def record_result(self, report) -> None:
        module = report.nodeid.split("::")[0]
        self._results[module].append(report)
        if report.duration > self._durations[module]:
            self._durations[module] = report.duration

    def _parse_module(self, module: str) -> tuple[str, str]:
        """Extract (skill_name, test_name) from a module path."""
        parts = PurePosixPath(module).parts
        filename = PurePosixPath(module).stem
        if "skills" in parts:
            idx = list(parts).index("skills")
            skill = parts[idx + 1] if idx + 1 < len(parts) else "unknown"
            return (skill, filename)
        if "core" in parts:
            return ("core", filename)
        return ("other", filename)

    def build_table_rows(self) -> list[dict]:
        rows = []
        for module, reports in sorted(self._results.items()):
            skill, test = self._parse_module(module)
            passed = sum(1 for r in reports if r.passed)
            total = len(reports)
            duration = self._durations[module]
            failures = [r for r in reports if r.failed]
            rows.append(
                {
                    "skill": skill,
                    "test": test,
                    "passed": passed,
                    "total": total,
                    "duration": duration,
                    "failures": failures,
                    "module": module,
                }
            )
        return rows

    def compute_totals(self) -> dict:
        all_reports = [r for reports in self._results.values() for r in reports]
        return {
            "passed": sum(1 for r in all_reports if r.passed),
            "total": len(all_reports),
        }

    def format_table(self) -> str:
        rows = self.build_table_rows()
        totals = self.compute_totals()
        lines = []
        lines.append(f"{'Skill':<17}{'Test':<28}{'Result':<9}{'Time'}")
        total_duration = 0.0
        for row in rows:
            result = f"{row['passed']}/{row['total']}"
            time_str = f"{row['duration']:.1f}s"
            total_duration += row["duration"]
            lines.append(f"{row['skill']:<17}{row['test']:<28}{result:<9}{time_str}")
        lines.append(
            f"{'':<17}{'':<28}{totals['passed']}/{totals['total']:<9}{total_duration:.1f}s"
        )
        return "\n".join(lines)

    def format_failures(self) -> str:
        lines = []
        for row in self.build_table_rows():
            for report in row["failures"]:
                lines.append(f"\n{report.nodeid}")
                if report.longreprtext:
                    lines.append(f"  {report.longreprtext}")
        return "\n".join(lines)


# --- Pytest plugin hooks ---

_reporter: EvalReporter | None = None


def pytest_configure(config) -> None:
    global _reporter
    _reporter = EvalReporter(verbose=False)


def pytest_report_header(config) -> None:
    if _reporter is not None:
        _reporter.verbose = config.getoption("verbose", default=False)


def pytest_runtest_logreport(report) -> None:
    if _reporter is None:
        return
    if report.when != "call":
        return
    _reporter.record_result(report)


def pytest_terminal_summary(terminalreporter, config) -> None:
    if _reporter is None:
        return
    rows = _reporter.build_table_rows()
    if not rows:
        return

    tw = terminalreporter._tw
    tw.sep("=", "Eval Summary")
    tw.line()
    tw.line(_reporter.format_table())

    failure_text = _reporter.format_failures()
    if failure_text.strip():
        tw.line()
        tw.sep("=", "FAILURES")
        tw.line(failure_text)
