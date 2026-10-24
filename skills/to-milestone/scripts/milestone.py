#!/usr/bin/env python3
"""Create a GitHub milestone from a plan file, then back-fill the spec's issue table.

Usage:
    python3 milestone.py create PLAN.json --dry-run
    python3 milestone.py create PLAN.json --result RESULT.json
    python3 milestone.py backfill SPEC.md --result RESULT.json

`create` validates the plan, then either prints every `gh api` call (`--dry-run`, or when
`gh` cannot reach the repo) or makes them: the milestone, any missing labels, every issue
with a stub body, the real bodies, the blocked-by links, and a read-back of each issue's
blockers. A body names another planned issue as `{#<key>}`; the stubs exist before any
real body is written, so a forward reference always resolves.

`backfill` rewrites only the spec's issue table (`#` and `Depends on` cells), the node
labels of the mermaid graph under it, and the `Milestone:` header line. Prose is untouched.

Exit codes: 0 done; 1 a GitHub call failed or a blocker read back wrong; 2 the plan or
spec is invalid; 3 `gh` cannot reach the repo, so nothing was created.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

CLOSER_LABEL = "milestone-closer"
PLACEHOLDER_RE = re.compile(r"\{#([^}\s]+)\}")
EXTERNAL_RE = re.compile(r"^#(\d+)$")
REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")
ATTRIBUTION_RE = re.compile(
    r"generated (with|by) \[?claude|co-authored-by:|\U0001f916", re.IGNORECASE
)


class PlanError(Exception):
    """The plan or spec cannot be used as written."""


class GhError(Exception):
    """A `gh api` call failed."""


def load_plan(plan_path: Path) -> dict:
    """Read a plan file, inlining each issue's `body_file` relative to the plan.

    Args:
        plan_path: The plan JSON.

    Returns:
        The plan, every issue carrying a `body`.

    Raises:
        PlanError: if the file or a body file cannot be read.
    """
    try:
        plan = json.loads(plan_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise PlanError(f"cannot read plan {plan_path}: {error}") from error

    for issue in plan.get("issues", []):
        if "body_file" in issue:
            body_path = plan_path.parent / issue["body_file"]
            try:
                issue["body"] = body_path.read_text()
            except OSError as error:
                raise PlanError(f"issue {issue.get('key')}: cannot read {body_path}") from error

    return plan


def validate(plan: dict) -> list[str]:
    """Return every problem with the plan; an empty list means it is safe to run."""
    problems = []
    issues = plan.get("issues", [])
    keys = [str(issue.get("key", "")) for issue in issues]
    label_names = {label.get("name") for label in plan.get("labels", [])}
    milestone = plan.get("milestone", {})

    if not REPO_RE.match(plan.get("repo", "")):
        problems.append("repo must be owner/name")
    if not milestone.get("title"):
        problems.append("milestone.title is missing")
    if "Spec:" not in milestone.get("description", ""):
        problems.append("milestone.description must end with 'Spec: <path>'")
    if not issues:
        problems.append("the plan has no issues")
    if len(set(keys)) != len(keys) or "" in keys:
        problems.append("every issue needs a unique, non-empty key")

    for issue in issues:
        key = str(issue.get("key", ""))
        if not issue.get("title"):
            problems.append(f"issue {key}: title is missing")
        if not issue.get("body"):
            problems.append(f"issue {key}: body is missing")
        for blocker in issue.get("blocked_by", []):
            if blocker == key:
                problems.append(f"issue {key}: blocked by itself")
            elif blocker not in keys and not EXTERNAL_RE.match(blocker):
                problems.append(f"issue {key}: blocker {blocker!r} is neither a key nor #<number>")
        for placeholder in PLACEHOLDER_RE.findall(issue.get("body", "")):
            if placeholder not in keys:
                problems.append(f"issue {key}: body names {{#{placeholder}}}, which is not a key")
        for label in issue.get("labels", []):
            if label not in label_names:
                problems.append(f"issue {key}: label {label!r} is not in the plan's labels")
        if ATTRIBUTION_RE.search(issue.get("body", "")):
            problems.append(f"issue {key}: body carries an AI attribution line")

    if ATTRIBUTION_RE.search(milestone.get("description", "")):
        problems.append("milestone.description carries an AI attribution line")

    problems.extend(_closer_problems(issues))
    if not problems:
        try:
            creation_order(issues)
        except PlanError as error:
            problems.append(str(error))

    return problems


def _closer_problems(issues: list[dict]) -> list[str]:
    """Check that closer 1 waits on every other issue and each later closer on the one before."""
    closers = [issue for issue in issues if CLOSER_LABEL in issue.get("labels", [])]
    others = {str(issue["key"]) for issue in issues if issue not in closers}
    problems = []

    for index, closer in enumerate(closers):
        blockers = set(closer.get("blocked_by", []))
        required = others if index == 0 else {str(closers[index - 1]["key"])}
        missing = sorted(required - blockers)
        if missing:
            problems.append(
                f"closer {closer['key']}: must be blocked by {', '.join(missing)} as well"
            )

    return problems


def creation_order(issues: list[dict]) -> list[dict]:
    """Order issues so each comes after its in-plan blockers, otherwise keeping plan order.

    Raises:
        PlanError: if the blockers form a cycle.
    """
    by_key = {str(issue["key"]): issue for issue in issues}
    ordered: list[dict] = []
    placed: set[str] = set()

    while len(ordered) < len(issues):
        ready = [
            issue
            for issue in issues
            if str(issue["key"]) not in placed
            and all(b in placed for b in issue.get("blocked_by", []) if b in by_key)
        ]
        if not ready:
            stuck = sorted(key for key in by_key if key not in placed)
            raise PlanError(f"blockers form a cycle among issues {', '.join(stuck)}")
        ordered.append(ready[0])
        placed.add(str(ready[0]["key"]))

    return ordered


def resolve_body(body: str, issue_numbers: Mapping[str, int | str]) -> str:
    """Replace each `{#key}` with `#<number>` from the created issues."""
    return PLACEHOLDER_RE.sub(lambda match: f"#{issue_numbers[match.group(1)]}", body)


def stub_body(milestone_title: str) -> str:
    """The placeholder body an issue carries until every issue exists."""
    return f"Part of the {milestone_title} milestone. The full body follows in a moment."


class DryRun:
    """Prints each call as a pasteable `gh api` command instead of making it."""

    def __init__(self) -> None:
        """Start with no output."""
        self.lines: list[str] = []

    def call(self, method: str, path: str, body: dict | None = None, note: str = "") -> None:
        """Record one call."""
        if note:
            self.lines.append(f"# {note}")
        if body is None:
            self.lines.append(f"gh api -X {method} '{path}'")
        else:
            payload = json.dumps(body, indent=2, ensure_ascii=False)
            self.lines.append(f"gh api -X {method} '{path}' --input - <<'JSON'\n{payload}\nJSON")


def gh_api(method: str, path: str, body: dict | None = None):
    """Make one `gh api` call and return its parsed JSON.

    Raises:
        GhError: if `gh` exits non-zero or prints something that is not JSON.
    """
    command = ["gh", "api", "-X", method, path]
    if body is not None:
        command += ["--input", "-"]
    completed = subprocess.run(
        command,
        input=None if body is None else json.dumps(body),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise GhError(f"gh api -X {method} {path}: {detail}")

    try:
        return json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError as error:
        raise GhError(f"gh api -X {method} {path}: not JSON: {completed.stdout[:200]}") from error


def print_plan(plan: dict, ordered: list[dict]) -> None:
    """Print the milestone and its issues in creation order."""
    milestone = plan["milestone"]
    print(f"Milestone: {milestone['title']} on {plan['repo']}")
    print(f"  {milestone['description']}")
    for position, issue in enumerate(ordered, start=1):
        labels = f" [{', '.join(issue['labels'])}]" if issue.get("labels") else ""
        blockers = ", ".join(issue.get("blocked_by", [])) or "nothing"
        print(f"  {position}. ({issue['key']}) {issue['title']}{labels}; blocked by {blockers}")
    print()


def dry_run(plan: dict, ordered: list[dict]) -> str:
    """Return every call `create` would make, with unknown numbers shown as placeholders."""
    repo = plan["repo"]
    calls = DryRun()
    in_plan = {str(issue["key"]) for issue in ordered}
    numbers = {key: f"<number of {key}>" for key in in_plan}

    calls.call("GET", f"repos/{repo}", note="Preflight: gh can reach the repo")
    calls.call("GET", f"repos/{repo}/milestones?state=all&per_page=100", note="Stop if taken")
    calls.call("GET", f"repos/{repo}/labels?per_page=100")
    for label in plan.get("labels", []):
        calls.call("POST", f"repos/{repo}/labels", label, note="Only if missing")
    calls.call("POST", f"repos/{repo}/milestones", plan["milestone"])
    for issue in ordered:
        calls.call("POST", f"repos/{repo}/issues", _stub_payload(plan, issue, "<milestone>"))
    for issue in ordered:
        body = {"body": resolve_body(issue["body"], numbers)}
        calls.call("PATCH", f"repos/{repo}/issues/{numbers[issue['key']]}", body)
    for issue in ordered:
        for blocker in issue.get("blocked_by", []):
            blocker_id = f"<id of {blocker}>"
            if blocker not in in_plan:
                calls.call("GET", f"repos/{repo}/issues/{blocker[1:]}", note=f"id of {blocker}")
            path = f"repos/{repo}/issues/{numbers[issue['key']]}/dependencies/blocked_by"
            calls.call("POST", path, {"issue_id": blocker_id})
    for issue in ordered:
        path = f"repos/{repo}/issues/{numbers[issue['key']]}/dependencies/blocked_by"
        calls.call("GET", path, note="Verify blockers")

    return "\n".join(calls.lines)


def _stub_payload(plan: dict, issue: dict, milestone_number: int | str) -> dict:
    """The POST body that creates an issue with its stub body."""
    return {
        "title": issue["title"],
        "body": stub_body(plan["milestone"]["title"]),
        "milestone": milestone_number,
        "labels": issue.get("labels", []),
    }


def create(plan: dict, ordered: list[dict], result_path: Path) -> int:
    """Make every call, saving progress to `result_path` after each issue.

    Returns:
        0 when every blocker reads back as planned, 1 otherwise.

    Raises:
        GhError: if a call fails; the result file holds what was created.
    """
    repo = plan["repo"]
    milestone = plan["milestone"]
    result: dict = {"repo": repo, "milestone": None, "issues": {}}

    taken = gh_api("GET", f"repos/{repo}/milestones?state=all&per_page=100")
    if any(existing.get("title") == milestone["title"] for existing in taken):
        raise GhError(f"milestone {milestone['title']!r} already exists on {repo}; nothing created")

    existing_labels = {
        label["name"] for label in gh_api("GET", f"repos/{repo}/labels?per_page=100")
    }
    for label in plan.get("labels", []):
        if label["name"] not in existing_labels:
            gh_api("POST", f"repos/{repo}/labels", label)
            print(f"created label {label['name']}")

    created = gh_api("POST", f"repos/{repo}/milestones", milestone)
    result["milestone"] = {
        "number": created["number"],
        "url": created["html_url"],
        "title": milestone["title"],
    }
    _save(result, result_path)
    print(f"created milestone {milestone['title']}: {created['html_url']}")

    for issue in ordered:
        made = gh_api("POST", f"repos/{repo}/issues", _stub_payload(plan, issue, created["number"]))
        result["issues"][str(issue["key"])] = {
            "number": made["number"],
            "id": made["id"],
            "url": made["html_url"],
        }
        _save(result, result_path)
        print(f"created #{made['number']} {issue['title']}")

    numbers = {key: entry["number"] for key, entry in result["issues"].items()}
    for issue in ordered:
        body = {"body": resolve_body(issue["body"], numbers)}
        gh_api("PATCH", f"repos/{repo}/issues/{numbers[str(issue['key'])]}", body)

    return _link_and_verify(repo, ordered, result)


def _link_and_verify(repo: str, ordered: list[dict], result: dict) -> int:
    """Add each blocked-by link by the blocker's REST id, then read every issue's blockers back."""
    issue_ids = {key: entry["id"] for key, entry in result["issues"].items()}
    numbers = {key: entry["number"] for key, entry in result["issues"].items()}
    expected: dict[str, set[int]] = {}

    for issue in ordered:
        key = str(issue["key"])
        expected[key] = set()
        for blocker in issue.get("blocked_by", []):
            if blocker in issue_ids:
                blocker_id, blocker_number = issue_ids[blocker], numbers[blocker]
            else:
                blocker_number = int(blocker[1:])
                blocker_id = gh_api("GET", f"repos/{repo}/issues/{blocker_number}")["id"]
            path = f"repos/{repo}/issues/{numbers[key]}/dependencies/blocked_by"
            gh_api("POST", path, {"issue_id": blocker_id})
            expected[key].add(blocker_number)

    mismatches = []
    for issue in ordered:
        key = str(issue["key"])
        path = f"repos/{repo}/issues/{numbers[key]}/dependencies/blocked_by"
        actual = {blocker["number"] for blocker in gh_api("GET", path)}
        if actual != expected[key]:
            mismatches.append(
                f"#{numbers[key]}: expected blockers {_numbers(expected[key])}, "
                f"GitHub has {_numbers(actual)}"
            )

    for mismatch in mismatches:
        print(f"MISMATCH {mismatch}", file=sys.stderr)
    if not mismatches:
        print(f"verified the blockers of all {len(ordered)} issues")
    return 1 if mismatches else 0


def _numbers(issue_numbers: set[int]) -> str:
    """Format a set of issue numbers for a report line."""
    return ", ".join(f"#{number}" for number in sorted(issue_numbers)) or "none"


def _save(result: dict, result_path: Path) -> None:
    """Write the creation record so a failure part-way still says what exists."""
    result_path.write_text(json.dumps(result, indent=2) + "\n")


def gh_reaches(repo: str) -> str | None:
    """Return why `gh` cannot reach the repo, or None when it can."""
    if not shutil.which("gh"):
        return "gh is not installed"
    try:
        gh_api("GET", f"repos/{repo}")
    except GhError as error:
        return str(error)
    return None


def backfill(spec_text: str, result: dict) -> str:
    """Swap planned positions for issue numbers in the spec's issue table, graph, and header.

    Args:
        spec_text: The spec as written, positions in the table's `#` column.
        result: The record `create` saved.

    Returns:
        The spec with the table's `#` and `Depends on` cells, the graph's node labels, and the
        `Milestone:` line rewritten. Every other line is returned unchanged.

    Raises:
        PlanError: if the spec has no table with `#` and `Depends on` columns.
    """
    issues = result["issues"]
    lines = spec_text.split("\n")
    table_start, number_column, depends_column = _find_issue_table(lines)

    row = table_start + 2
    while row < len(lines) and lines[row].lstrip().startswith("|"):
        cells = lines[row].split("|")
        position = cells[number_column].strip()
        if position in issues:
            entry = issues[position]
            cells[number_column] = f" [#{entry['number']}]({entry['url']}) "
        cells[depends_column] = _backfill_depends(cells[depends_column], issues)
        lines[row] = "|".join(cells)
        row += 1

    _backfill_graph(lines, row, issues)
    _backfill_header(lines, result["milestone"])
    return "\n".join(lines)


def _find_issue_table(lines: list[str]) -> tuple[int, int, int]:
    """Return the issue table's header line and the split indexes of its `#` and `Depends on`."""
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().lower() for cell in line.split("|")]
        if "#" in cells and "depends on" in cells:
            return index, cells.index("#"), cells.index("depends on")
    raise PlanError("no issue table with '#' and 'Depends on' columns")


def _backfill_depends(cell: str, issues: dict) -> str:
    """Rewrite each comma-separated item that starts with a planned position."""
    items = []
    for item in cell.split(","):
        match = re.match(r"^(\s*)(\d+)\b(.*)$", item, re.DOTALL)
        if match and match.group(2) in issues:
            item = f"{match.group(1)}#{issues[match.group(2)]['number']}{match.group(3)}"
        items.append(item)
    return ",".join(items)


def _backfill_graph(lines: list[str], after: int, issues: dict) -> None:
    """Rewrite `[N label]` nodes in the mermaid block that follows the table, if any."""
    index = after
    while index < len(lines) and not lines[index].startswith("## "):
        if lines[index].strip().startswith("```mermaid"):
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                lines[index] = re.sub(
                    r'\[("?)(\d+)(\s)',
                    lambda match: (
                        f"[{match.group(1)}#{issues[match.group(2)]['number']}{match.group(3)}"
                        if match.group(2) in issues
                        else match.group(0)
                    ),
                    lines[index],
                )
                index += 1
            return
        index += 1


def _backfill_header(lines: list[str], milestone: dict) -> None:
    """Link the milestone from the `Milestone:` line above the first section, or add one."""
    link = f"[{milestone['title']}]({milestone['url']})"
    first_section = next(
        (index for index, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )

    for index in range(first_section):
        if "Milestone:" in lines[index]:
            lines[index] = re.sub(
                r"Milestone:\s*(`[^`]*`|\[[^\]]*\]\([^)]*\)|[^·\n]*?)(?=\s*·|\s*$)",
                f"Milestone: {link}",
                lines[index],
                count=1,
            )
            return

    title_line = next((index for index in range(first_section) if lines[index].startswith("# ")), 0)
    lines[title_line + 1 : title_line + 1] = ["", f"Milestone: {link}"]


def main(argv: list[str] | None = None) -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create", help="create the milestone from a plan")
    create_parser.add_argument("plan", type=Path)
    create_parser.add_argument("--dry-run", action="store_true", help="print the calls only")
    create_parser.add_argument("--result", type=Path, help="where to save what was created")
    backfill_parser = commands.add_parser("backfill", help="put issue numbers in the spec")
    backfill_parser.add_argument("spec", type=Path)
    backfill_parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "backfill":
            result = json.loads(arguments.result.read_text())
            arguments.spec.write_text(backfill(arguments.spec.read_text(), result))
            print(f"back-filled {arguments.spec}")
            return 0
        return _run_create(arguments)
    except PlanError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _run_create(arguments: argparse.Namespace) -> int:
    """Validate the plan, then print or make the calls."""
    plan = load_plan(arguments.plan)
    problems = validate(plan)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 2

    ordered = creation_order(plan["issues"])
    print_plan(plan, ordered)
    if arguments.dry_run:
        print(dry_run(plan, ordered))
        return 0

    unreachable = gh_reaches(plan["repo"])
    if unreachable:
        print(f"gh cannot reach {plan['repo']} ({unreachable}). Nothing was created.")
        print("Run these calls where gh can, or fix gh and re-run:\n")
        print(dry_run(plan, ordered))
        return 3

    result_path = arguments.result or arguments.plan.with_name("milestone-result.json")
    try:
        return create(plan, ordered, result_path)
    except GhError as error:
        print(f"error: {error}", file=sys.stderr)
        print(f"Created so far is recorded in {result_path}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
