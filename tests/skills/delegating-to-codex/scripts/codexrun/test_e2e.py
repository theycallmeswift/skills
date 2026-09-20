"""End-to-end round trip against the real Codex CLI: implement, resume, review.

The unit tests and evals use a fake `codex`, so they can't catch drift in the real CLI
(renamed flags, `exec resume` options, the event stream, schema enforcement). This test
can. It costs a few cents and a minute or two, so it is opt-in:

    make test:e2e

It needs `codex` on PATH and `codex login status` passing.
"""

from __future__ import annotations

import json
import shutil

import pytest
from support.codex import Repo

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not shutil.which("codex"), reason="needs a signed-in `codex` on PATH"),
]


def test_implement_resume_review_round_trip(tmp_path):
    repo = Repo(tmp_path)
    repo.path.mkdir()
    repo.git("init", "-q", "-b", "main")
    repo.git("commit", "-q", "--allow-empty", "-m", "init")
    head = repo.git("rev-parse", "HEAD")

    brief = repo.input("brief.md", "Create hello.txt containing exactly: hi\n")
    first = repo.start("implement", brief)
    assert (repo.path / "hello.txt").read_text().strip() == "hi"
    assert "tokens: in " in repo.codex_run("result", first).stdout

    fix = repo.input("fix.md", "Also create bye.txt containing exactly: bye\n")
    repo.start("implement", fix, "--resume", first)
    assert (repo.path / "bye.txt").read_text().strip() == "bye"

    review_brief = repo.input("review.md", "Review the new files for typos.\n")
    review = repo.start("review", review_brief)
    result = json.loads(repo.codex_run("result", review, "--json").stdout)
    verdict = json.loads(result["last_message"])
    assert {"verdict", "summary", "findings", "next_steps"} <= verdict.keys()

    assert repo.git("rev-parse", "HEAD") == head, "Codex must not commit"
