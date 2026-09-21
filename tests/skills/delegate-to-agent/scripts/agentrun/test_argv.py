"""Tests for the exact `codex exec` command for each kind of job."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentrun import ASSETS
from agentrun.argv import build_argv

WORKTREE = Path("/wt")
JOB_DIR = Path("/state/job")
OUTPUT = ["-o", "/state/job/last.md", "-"]
REVIEW_SCHEMA = ASSETS / "review-output.schema.json"


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        pytest.param(
            {"effort": "high"},
            "codex exec --sandbox workspace-write --cd /wt --json --strict-config"
            " -c model_reasoning_effort=high",
            id="minimal",
        ),
        pytest.param(
            {"effort": "xhigh", "model": "m1", "tier": "flex", "network": True},
            "codex exec --sandbox workspace-write --cd /wt --json --strict-config"
            " -c model_reasoning_effort=xhigh -c service_tier=flex -m m1"
            " -c sandbox_workspace_write.network_access=true",
            id="all-flags",
        ),
        pytest.param(
            {"effort": "medium", "sandbox": "read-only", "model": "m", "tier": "t"},
            "codex exec --sandbox read-only --cd /wt --json --strict-config"
            " -c model_reasoning_effort=medium -c service_tier=t -m m",
            id="read-only",
        ),
        pytest.param(
            {"effort": "low", "thread_id": "T1", "tier": "fast", "model": "m2", "network": True},
            'codex exec resume T1 --json --strict-config -c sandbox_mode="workspace-write"'
            " -c model_reasoning_effort=low -c service_tier=fast -m m2"
            " -c sandbox_workspace_write.network_access=true",
            id="resume",
        ),
        pytest.param(
            {"effort": "low", "sandbox": "read-only", "thread_id": "T1"},
            'codex exec resume T1 --json --strict-config -c sandbox_mode="read-only"'
            " -c model_reasoning_effort=low",
            id="read-only-resume",
        ),
    ],
)
def test_argv(kwargs, expected):
    built = build_argv(worktree=WORKTREE, job_dir=JOB_DIR, **kwargs)

    assert built == [*expected.split(), *OUTPUT]


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"sandbox": "read-only"}, {"thread_id": "T1"}],
    ids=["fresh", "read-only", "resume"],
)
def test_schema_is_emitted_when_requested(kwargs):
    built = build_argv(
        worktree=WORKTREE,
        job_dir=JOB_DIR,
        effort="low",
        schema=REVIEW_SCHEMA,
        **kwargs,
    )

    assert built[-5:] == ["--output-schema", str(REVIEW_SCHEMA), *OUTPUT]


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"sandbox": "read-only"}, {"thread_id": "T1"}],
    ids=["fresh", "read-only", "resume"],
)
def test_no_schema_means_no_output_schema_flag(kwargs):
    built = build_argv(worktree=WORKTREE, job_dir=JOB_DIR, effort="low", **kwargs)

    assert "--output-schema" not in built


def test_resume_leaves_sandbox_and_cd_to_config_and_cwd():
    resumed = build_argv(
        worktree=WORKTREE,
        job_dir=JOB_DIR,
        effort="low",
        thread_id="T1",
    )

    assert resumed[:4] == ["codex", "exec", "resume", "T1"]
    assert "--cd" not in resumed and "--sandbox" not in resumed


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"sandbox": "read-only"},
        {"sandbox": "read-only", "schema": REVIEW_SCHEMA},
        {"thread_id": "T", "network": True},
    ],
    ids=["fresh", "read-only", "read-only-schema", "resume"],
)
def test_no_job_is_ephemeral(kwargs):
    built = build_argv(worktree=WORKTREE, job_dir=JOB_DIR, effort="low", **kwargs)

    assert "--ephemeral" not in built


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"thread_id": "T", "network": True}, {"sandbox": "read-only"}],
    ids=["fresh", "resume", "read-only"],
)
def test_never_escalates(kwargs):
    built = build_argv(
        worktree=WORKTREE,
        job_dir=JOB_DIR,
        effort="high",
        **kwargs,
    )

    assert "--ignore-user-config" not in built
    assert "--add-dir" not in built
    assert "--dangerously" not in " ".join(built)


def test_unknown_sandbox_is_rejected():
    with pytest.raises(ValueError, match="sandbox"):
        build_argv(
            worktree=WORKTREE,
            job_dir=JOB_DIR,
            effort="low",
            sandbox="danger-full-access",
        )
