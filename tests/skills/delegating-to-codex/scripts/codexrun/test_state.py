"""Tests for job state location, naming, and pruning."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import cast

import pytest
from codexrun import UsageError
from codexrun.state import (
    JobMeta,
    jobs_dir,
    list_jobs,
    new_job_id,
    prune_jobs,
    state_root,
    write_meta,
)
from support.codex import make_jobs


@pytest.mark.parametrize(
    "env, root",
    [
        (
            {"CLAUDE_PLUGIN_DATA": "/cpd", "HERMES_HOME": "/hh", "XDG_STATE_HOME": "/x"},
            "/cpd",
        ),
        ({"HERMES_HOME": "/hh", "XDG_STATE_HOME": "/x"}, "/hh/mechaswift"),
        ({"XDG_STATE_HOME": "/x", "HOME": "/h"}, "/x/mechaswift"),
        ({"HOME": "/h"}, "/h/.local/state/mechaswift"),
        ({"CLAUDE_PLUGIN_DATA": "", "HERMES_HOME": "", "HOME": "/h"}, "/h/.local/state/mechaswift"),
    ],
    ids=["plugin-data-wins", "hermes", "xdg", "home", "empty-values-ignored"],
)
def test_state_root_precedence(env, root):
    assert state_root(env) == Path(root)


def test_jobs_dir_is_keyed_by_worktree_path(tmp_path):
    env = {"CLAUDE_PLUGIN_DATA": "/cpd"}
    worktree = tmp_path / "my-repo"
    same_name_elsewhere = tmp_path / "other" / "my-repo"
    worktree.mkdir()
    same_name_elsewhere.mkdir(parents=True)
    digest = hashlib.sha256(str(worktree.resolve()).encode()).hexdigest()[:16]

    assert jobs_dir(env, worktree) == Path("/cpd/codex-jobs") / f"my-repo-{digest}"
    assert jobs_dir(env, worktree) == jobs_dir(env, worktree)
    assert jobs_dir(env, same_name_elsewhere) != jobs_dir(env, worktree)


def test_job_id_is_timestamp_slug_and_random_suffix():
    assert re.fullmatch(r"\d{8}-\d{6}-review-[0-9a-f]{4}", new_job_id("review"))


def test_prune_keeps_the_newest(tmp_path):
    make_jobs(tmp_path, 60)

    prune_jobs(tmp_path, keep=50)

    left = sorted(job_dir.name for job_dir in tmp_path.iterdir())
    assert len(left) == 50
    assert (left[0], left[-1]) == ("job10", "job59")


def test_prune_is_a_noop_under_the_limit(tmp_path):
    make_jobs(tmp_path, 3)

    prune_jobs(tmp_path, keep=50)

    assert len(list(tmp_path.iterdir())) == 3


@pytest.mark.parametrize("created_at", [None, "not-a-timestamp"], ids=["missing", "invalid"])
def test_write_meta_rejects_invalid_created_at(tmp_path, created_at):
    job_dir = tmp_path / "invalid"
    job_dir.mkdir()
    meta = cast(JobMeta, {} if created_at is None else {"created_at": created_at})

    with pytest.raises((KeyError, ValueError)):
        write_meta(job_dir, meta)


@pytest.mark.parametrize(
    "contents",
    ["{}", '{"created_at": "not-a-timestamp"}', "not json"],
    ids=["missing", "invalid", "corrupt"],
)
def test_list_jobs_surfaces_the_bad_job_id(tmp_path, contents):
    job_dir = tmp_path / "bad-job"
    job_dir.mkdir()
    (job_dir / "meta.json").write_text(contents)

    with pytest.raises(UsageError, match="bad-job"):
        list_jobs(tmp_path)
