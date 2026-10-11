"""Tests for milestone.py against a fake `gh` on PATH.

Covers the plan checks, the dry run, the live order (stubs before bodies, links by REST id,
blockers read back), the fallback when gh cannot reach the repo, and the spec back-fill.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import milestone
import pytest

FAKE_GH = Path(__file__).with_name("fake_gh.py")
REPO = "acme/ledger"


def make_plan() -> dict:
    """A plan with a forward reference, an outside blocker, a lockfile issue, and two closers."""
    labels = ["lockfile", "spike", "needs-human", "milestone-closer"]
    return {
        "repo": REPO,
        "milestone": {
            "title": "Export",
            "description": "Accounts export to CSV and Excel. Spec: docs/specs/export.md",
        },
        "labels": [{"name": name, "color": "ededed", "description": name} for name in labels],
        "issues": [
            {"key": "1", "title": "Export core", "body": "Depends on: nothing.", "blocked_by": []},
            {
                "key": "2",
                "title": "Export command",
                "body": "**Depends on:** {#1} (the writer), {#4} (the filter).",
                "blocked_by": ["1", "4", "#155"],
            },
            {
                "key": "3",
                "title": "Excel output",
                "body": "**Depends on:** {#1}.",
                "labels": ["lockfile"],
                "blocked_by": ["1"],
            },
            {"key": "4", "title": "Date filter", "body": "Depends on: nothing.", "blocked_by": []},
            {
                "key": "5",
                "title": "Closer 1/2",
                "body": "**Depends on:** every other issue.",
                "labels": ["milestone-closer"],
                "blocked_by": ["1", "2", "3", "4"],
            },
            {
                "key": "6",
                "title": "Closer 2/2",
                "body": "**Depends on:** {#5}.",
                "labels": ["milestone-closer"],
                "blocked_by": ["5"],
            },
        ],
    }


class FakeGitHub:
    """The fake gh's state file and call log, with `gh` on PATH."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Install the fake as `gh` and seed one issue outside the milestone, #155."""
        bindir = root / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_GH} "$@"\n')
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

        self.state_path = root / "state.json"
        self.log_path = root / "calls.log"
        self.log_path.write_text("")
        existing = {"number": 155, "id": 1155, "title": "Carve-out", "blocked_by": []}
        self.state_path.write_text(
            json.dumps(
                {
                    "repo": REPO,
                    "labels": [{"name": "spike"}],
                    "issues": {"155": existing},
                    "next_number": 200,
                }
            )
        )
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        monkeypatch.setenv("FAKE_GH_STATE", str(self.state_path))
        monkeypatch.setenv("FAKE_GH_LOG", str(self.log_path))

    @property
    def state(self) -> dict:
        """The fake's current state."""
        return json.loads(self.state_path.read_text())

    @property
    def calls(self) -> list[str]:
        """Every argv the fake received, in order."""
        return self.log_path.read_text().splitlines()

    def issue(self, title: str) -> dict:
        """The created issue with this title."""
        return next(issue for issue in self.state["issues"].values() if issue["title"] == title)


@pytest.fixture
def github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    """A fake GitHub behind `gh`."""
    return FakeGitHub(tmp_path, monkeypatch)


@pytest.fixture
def plan_path(tmp_path: Path) -> Path:
    """The default plan, written to disk."""
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(make_plan()))
    return path


def write_plan(tmp_path: Path, plan: dict) -> Path:
    """Write a plan and return its path."""
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path


def test_valid_plan_has_no_problems():
    assert milestone.validate(make_plan()) == []


def test_unknown_placeholder_is_rejected():
    plan = make_plan()
    plan["issues"][0]["body"] = "Builds on {#9}."

    assert any("{#9}" in problem for problem in milestone.validate(plan))


def test_cycle_is_rejected():
    plan = make_plan()
    plan["issues"][0]["blocked_by"] = ["2"]

    assert any("cycle" in problem for problem in milestone.validate(plan))


def test_first_closer_missing_a_blocker_is_rejected():
    plan = make_plan()
    plan["issues"][4]["blocked_by"] = ["1"]

    problems = milestone.validate(plan)

    assert any("closer 5" in problem and "2, 3, 4" in problem for problem in problems)


def test_second_closer_must_wait_on_the_first():
    plan = make_plan()
    plan["issues"][5]["blocked_by"] = ["4"]

    assert any("closer 6" in problem for problem in milestone.validate(plan))


@pytest.mark.parametrize(
    "footer",
    ["🤖 Generated with [Claude Code](https://claude.com/claude-code)", "Co-Authored-By: A <a@b>"],
)
def test_attribution_footer_is_rejected(footer: str):
    plan = make_plan()
    plan["issues"][0]["body"] += f"\n\n---\n{footer}\n"

    assert any("attribution" in problem for problem in milestone.validate(plan))


def test_label_outside_the_plan_is_rejected():
    plan = make_plan()
    plan["issues"][0]["labels"] = ["lockfle"]

    assert any("lockfle" in problem for problem in milestone.validate(plan))


def test_description_without_spec_path_is_rejected():
    plan = make_plan()
    plan["milestone"]["description"] = "Accounts export to CSV."

    assert any("Spec:" in problem for problem in milestone.validate(plan))


def test_creation_order_puts_blockers_first():
    ordered = milestone.creation_order(make_plan()["issues"])

    assert [issue["key"] for issue in ordered] == ["1", "3", "4", "2", "5", "6"]


def test_body_file_is_read_relative_to_the_plan(tmp_path: Path):
    plan = make_plan()
    del plan["issues"][0]["body"]
    plan["issues"][0]["body_file"] = "bodies/1.md"
    (tmp_path / "bodies").mkdir()
    (tmp_path / "bodies" / "1.md").write_text("## Goal\nRows to CSV.\n")

    loaded = milestone.load_plan(write_plan(tmp_path, plan))

    assert loaded["issues"][0]["body"] == "## Goal\nRows to CSV.\n"


def test_invalid_plan_exits_2_and_calls_nothing(github: FakeGitHub, tmp_path: Path, capsys):
    plan = make_plan()
    plan["issues"][1]["blocked_by"] = ["7"]

    code = milestone.main(["create", str(write_plan(tmp_path, plan))])

    assert code == 2
    assert "blocker '7'" in capsys.readouterr().err
    assert github.calls == []


def test_dry_run_prints_every_call_and_makes_none(github: FakeGitHub, plan_path: Path, capsys):
    code = milestone.main(["create", str(plan_path), "--dry-run"])
    output = capsys.readouterr().out

    assert code == 0
    assert github.calls == []
    assert output.count(f"gh api -X POST 'repos/{REPO}/issues' --input -") == 6
    assert output.count("/dependencies/blocked_by' --input -") == 9
    assert "#<number of 4> (the filter)" in output
    assert f"gh api -X GET 'repos/{REPO}/issues/155'" in output


def test_live_run_creates_stubs_before_bodies_and_links_by_id(
    github: FakeGitHub, plan_path: Path, tmp_path: Path
):
    result_path = tmp_path / "result.json"

    code = milestone.main(["create", str(plan_path), "--result", str(result_path)])

    assert code == 0
    calls = github.calls
    last_stub = max(index for index, call in enumerate(calls) if call.endswith("/issues --input -"))
    first_patch = min(index for index, call in enumerate(calls) if "-X PATCH" in call)
    assert last_stub < first_patch

    command, filter_, closer = (
        github.issue(title) for title in ("Export command", "Date filter", "Closer 1/2")
    )
    assert f"#{filter_['number']} (the filter)" in command["body"]
    assert sorted(command["blocked_by"]) == sorted([200, filter_["number"], 155])
    assert len(closer["blocked_by"]) == 4
    assert github.issue("Excel output")["labels"] == ["lockfile"]
    assert github.issue("Excel output")["milestone"] == 1


def test_live_run_creates_only_missing_labels(github: FakeGitHub, plan_path: Path, tmp_path: Path):
    milestone.main(["create", str(plan_path), "--result", str(tmp_path / "result.json")])

    created = [
        call for call in github.calls if call.startswith(f"gh api -X POST repos/{REPO}/labels")
    ]
    assert len(created) == 3
    assert [label["name"] for label in github.state["labels"]].count("spike") == 1


def test_live_run_saves_numbers_and_ids(github: FakeGitHub, plan_path: Path, tmp_path: Path):
    result_path = tmp_path / "result.json"

    milestone.main(["create", str(plan_path), "--result", str(result_path)])
    result = json.loads(result_path.read_text())

    assert result["milestone"]["url"] == f"https://github.com/{REPO}/milestone/1"
    assert result["issues"]["1"] == {
        "number": 200,
        "id": 1200,
        "url": f"https://github.com/{REPO}/issues/200",
    }


def test_blockers_that_do_not_read_back_are_reported(
    github: FakeGitHub, plan_path: Path, tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("FAKE_GH_MAX_LINKS", "1")

    code = milestone.main(["create", str(plan_path), "--result", str(tmp_path / "result.json")])
    closer = github.issue("Closer 1/2")["number"]

    assert code == 1
    assert (
        f"MISMATCH #{closer}: expected blockers #200, #201, #202, #203" in capsys.readouterr().err
    )


def test_existing_milestone_stops_before_creating(
    github: FakeGitHub, plan_path: Path, tmp_path: Path, capsys
):
    state = github.state
    state["milestones"] = [{"title": "Export", "number": 4}]
    github.state_path.write_text(json.dumps(state))

    code = milestone.main(["create", str(plan_path), "--result", str(tmp_path / "result.json")])

    assert code == 1
    assert "already exists" in capsys.readouterr().err
    assert not any("-X POST" in call or "-X PATCH" in call for call in github.calls)


def test_failure_part_way_records_what_was_created(
    github: FakeGitHub, plan_path: Path, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("FAKE_GH_FAIL_ON", "PATCH issues/")
    result_path = tmp_path / "result.json"

    code = milestone.main(["create", str(plan_path), "--result", str(result_path)])

    assert code == 1
    assert len(json.loads(result_path.read_text())["issues"]) == 6


def test_unreachable_gh_prints_the_calls_and_creates_nothing(
    github: FakeGitHub, plan_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("FAKE_GH_OFFLINE", "1")

    code = milestone.main(["create", str(plan_path)])
    output = capsys.readouterr().out

    assert code == 3
    assert "Nothing was created" in output
    assert f"gh api -X POST 'repos/{REPO}/milestones' --input -" in output
    assert github.calls == [f"gh api -X GET repos/{REPO}"]


SPEC = """\
# Export milestone

Status: proposed · Owner: Dana · Milestone: `Export` · Scoped on 2026-10-07.

Step 1 writes rows; see issue 2 of the old plan, and 1, 4 stay as written here.

## Issues

| # | Title | Scope | Owns | Depends on |
| --- | --- | --- | --- | --- |
| 1 | Export core | Rows, step 1 then step 2 | `src/export.py` | |
| 2 | Export command | Wires 1 and 4 | `src/cli.py` | 1, 4, Brain #166 (the schema), step 3 |
| 3 | Closer 1/2 | Tidy | The milestone's files | every other issue in the milestone |

```mermaid
flowchart LR
    I1[1 export core] --> I2["2 export command"]
    I4[4 date filter] --> I2
```

Done when issue 1 ships.
"""

RESULT = {
    "repo": REPO,
    "milestone": {
        "number": 3,
        "url": "https://github.com/acme/ledger/milestone/3",
        "title": "Export",
    },
    "issues": {
        key: {"number": 300 + int(key), "id": 1300 + int(key), "url": f"https://x/{300 + int(key)}"}
        for key in ("1", "2", "3", "4")
    },
}


def test_backfill_rewrites_the_table_graph_and_header_only():
    lines = milestone.backfill(SPEC, RESULT).split("\n")

    assert lines[2] == (
        "Status: proposed · Owner: Dana · Milestone: "
        "[Export](https://github.com/acme/ledger/milestone/3) · Scoped on 2026-10-07."
    )
    assert lines[4] == SPEC.split("\n")[4]
    assert (
        lines[10]
        == "| [#301](https://x/301) | Export core | Rows, step 1 then step 2 | `src/export.py` | |"
    )
    assert lines[11] == (
        "| [#302](https://x/302) | Export command | Wires 1 and 4 | `src/cli.py` "
        "| #301, #304, Brain #166 (the schema), step 3 |"
    )
    assert lines[12].endswith("| every other issue in the milestone |")
    assert lines[16] == '    I1[#301 export core] --> I2["#302 export command"]'
    assert lines[-2] == "Done when issue 1 ships."


def test_backfill_is_idempotent():
    once = milestone.backfill(SPEC, RESULT)

    assert milestone.backfill(once, RESULT) == once


def test_backfill_adds_a_milestone_line_when_the_header_has_none():
    spec = SPEC.replace(" · Milestone: `Export`", "")

    lines = milestone.backfill(spec, RESULT).split("\n")

    assert lines[1:3] == ["", "Milestone: [Export](https://github.com/acme/ledger/milestone/3)"]


def test_backfill_without_an_issue_table_exits_2(tmp_path: Path, capsys):
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Spec\n\nNo table.\n")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(RESULT))

    code = milestone.main(["backfill", str(spec_path), "--result", str(result_path)])

    assert code == 2
    assert "no issue table" in capsys.readouterr().err
