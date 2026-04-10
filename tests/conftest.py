import os

import pytest

from tests.support.harness import ClaudeRunner


@pytest.fixture(scope="session")
def runner():
    """Session-scoped ClaudeRunner. Shared across all tests — each run() is a fresh subprocess."""
    return ClaudeRunner(
        model=os.environ.get("CLAUDE_TEST_MODEL", "haiku"),
        timeout=int(os.environ.get("CLAUDE_TEST_TIMEOUT", "30")),
    )
