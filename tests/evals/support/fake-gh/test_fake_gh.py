"""fake-gh's cassette against the real gh, and the fake's replay of that cassette.

The contract test needs no credentials and no internet, only the `gh` binary and a loopback
port. It skips without `gh`; GitHub's ubuntu runners ship it, so CI always runs it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from support.gh_contract import CASSETTE, COMMANDS, FAKE_GH, record

RE_RECORD = "gh output drifted; re-record with `uv run python tests/support/gh_contract.py`"


def entries(cassette: str) -> dict[str, str]:
    """Split a cassette into `? <exit code>` plus stdout, keyed by its `gh ...` line."""
    chunks = re.split(r"^\$ ", cassette, flags=re.MULTILINE)[1:]
    return {command: replay for command, _, replay in (chunk.partition("\n") for chunk in chunks)}


@pytest.mark.skipif(not shutil.which("gh"), reason="`gh` is not installed")
def test_real_gh_still_matches_the_cassette():
    recorded = entries(CASSETTE.read_text())
    live = entries(record())
    # The version records which gh made the cassette; any other gh may check it.
    del recorded["gh --version"], live["gh --version"]

    assert live == recorded, RE_RECORD


@pytest.mark.parametrize("command", COMMANDS, ids=" ".join)
def test_fake_replays_the_cassette(command: list[str], tmp_path: Path):
    result = subprocess.run(
        [FAKE_GH / "gh", *command],
        capture_output=True,
        text=True,
        env={**os.environ, "FAKE_GH_LOG_DIR": str(tmp_path)},
    )

    replay = f"? {result.returncode}\n{result.stdout}"
    assert replay == entries(CASSETTE.read_text())[f"gh {' '.join(command)}"]
