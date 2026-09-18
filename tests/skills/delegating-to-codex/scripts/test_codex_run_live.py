"""Live round trip against the real Codex CLI: implement, resume, review.

The unit tests and evals use a fake `codex`, so they can't catch drift in the real CLI
(renamed flags, `exec resume` options, the event stream, schema enforcement). This test
can. It costs a few cents and a minute or two, so it is opt-in:

    CODEX_LIVE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/skills/delegating-to-codex

It needs `codex` on PATH and `codex login status` passing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "skills"
    / "delegating-to-codex"
    / "scripts"
    / "codex_run.py"
)

pytestmark = pytest.mark.skipif(
    os.environ.get("CODEX_LIVE") != "1" or not shutil.which("codex"),
    reason="live Codex test; set CODEX_LIVE=1 with a logged-in codex on PATH",
)


def run(repo: Path, env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--cd", str(repo)],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )


def job_id(out: str) -> str:
    return next(line.split()[1] for line in out.splitlines() if line.startswith("job "))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def test_implement_resume_review_round_trip(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "--allow-empty",
        "-m", "init")  # fmt: skip
    head = git(repo, "rev-parse", "HEAD").strip()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "brief.md").write_text("Create hello.txt containing exactly: hi\n")
    (inputs / "fix.md").write_text("Also create bye.txt containing exactly: bye\n")
    (inputs / "review.md").write_text("Review the new files for typos.\n")
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path / "state")}
    env.pop("CODEX_THREAD_ID", None)

    first = run(repo, env, "start", "implement", "--effort", "low",
                "--brief", str(inputs / "brief.md"), "--wait")  # fmt: skip
    assert first.returncode == 0, first.stdout + first.stderr
    assert (repo / "hello.txt").read_text().strip() == "hi"
    assert "tokens: in " in first.stdout

    jid = job_id(first.stdout)
    second = run(repo, env, "start", "implement", "--resume", jid, "--effort", "low",
                 "--brief", str(inputs / "fix.md"), "--wait")  # fmt: skip
    assert second.returncode == 0, second.stdout + second.stderr
    assert (repo / "bye.txt").read_text().strip() == "bye"

    review = run(repo, env, "start", "review", "--effort", "low",
                 "--brief", str(inputs / "review.md"), "--wait")  # fmt: skip
    assert review.returncode == 0, review.stdout + review.stderr
    result = run(repo, env, "result", job_id(review.stdout), "--json")
    last = json.loads(json.loads(result.stdout)["last_message"])
    assert {"verdict", "summary", "findings", "next_steps"} <= last.keys()

    assert git(repo, "rev-parse", "HEAD").strip() == head, "Codex must not commit"
