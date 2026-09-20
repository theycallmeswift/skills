"""Tests for the exact `codex exec` command for each kind of job."""

from __future__ import annotations

from pathlib import Path

import pytest
from codexrun import ASSETS
from support.codex import argv as build_test_argv

WORKTREE = Path("/wt")
JOB_DIR = Path("/state/job")
OUTPUT = ["-o", "/state/job/last.md", "-"]
SCHEMA = str(ASSETS / "review-output.schema.json")


@pytest.mark.parametrize(
    "kwargs, head",
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
            {"effort": "low", "thread_id": "T1", "tier": "fast", "model": "m2", "network": True},
            'codex exec resume T1 --json --strict-config -c sandbox_mode="workspace-write"'
            " -c model_reasoning_effort=low -c service_tier=fast -m m2"
            " -c sandbox_workspace_write.network_access=true",
            id="resume",
        ),
    ],
)
def test_implement_argv(kwargs, head):
    built = build_test_argv("implement", worktree=WORKTREE, job_dir=JOB_DIR, **kwargs)
    assert built == [*head.split(), *OUTPUT]


@pytest.mark.parametrize(
    "kwargs, head",
    [
        pytest.param(
            {"effort": "low"},
            "codex exec --sandbox read-only --ephemeral --cd /wt --json --strict-config"
            " -c model_reasoning_effort=low",
            id="minimal",
        ),
        pytest.param(
            {"effort": "medium", "model": "m", "tier": "t"},
            "codex exec --sandbox read-only --ephemeral --cd /wt --json --strict-config"
            " -c model_reasoning_effort=medium -c service_tier=t -m m",
            id="model-and-tier",
        ),
    ],
)
def test_review_argv(kwargs, head):
    built = build_test_argv("review", worktree=WORKTREE, job_dir=JOB_DIR, **kwargs)
    assert built == [*head.split(), "--output-schema", SCHEMA, *OUTPUT]


def test_resume_leaves_sandbox_and_cd_to_config_and_cwd():
    resumed = build_test_argv(
        "implement",
        worktree=WORKTREE,
        job_dir=JOB_DIR,
        effort="low",
        thread_id="T1",
    )

    assert resumed[:4] == ["codex", "exec", "resume", "T1"]
    assert "--cd" not in resumed and "--sandbox" not in resumed


@pytest.mark.parametrize(
    "mode, kwargs",
    [("implement", {}), ("implement", {"thread_id": "T", "network": True}), ("review", {})],
)
def test_never_escalates(mode, kwargs):
    built = build_test_argv(
        mode,
        worktree=WORKTREE,
        job_dir=JOB_DIR,
        effort="high",
        **kwargs,
    )

    assert "--ignore-user-config" not in built
    assert "--add-dir" not in built
    assert "--dangerously" not in " ".join(built)


@pytest.mark.parametrize("kwargs", [{"network": True}, {"thread_id": "T"}])
def test_review_rejects_network_and_resume(kwargs):
    with pytest.raises(ValueError):
        build_test_argv(
            "review",
            worktree=WORKTREE,
            job_dir=JOB_DIR,
            effort="low",
            **kwargs,
        )
