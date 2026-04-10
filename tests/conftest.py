import pytest

from tests.support.harness import ClaudeRunner


@pytest.fixture(scope="session")
def runner():
    """Session-scoped ClaudeRunner. Shared across all tests — each run() is a fresh subprocess."""
    return ClaudeRunner()
