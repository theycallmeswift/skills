import textwrap

import pytest

from tests.support.harness.setup import cleanup_globs, skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Scope a GitHub webhook system for MechaSwift that listens for \
                PR events and posts summaries to Slack. It should handle retries, \
                filter by repo, and be configurable per-channel. We're using \
                Node.js and already have a Slack bot token.\
            """),
            textwrap.dedent("""\
                Purpose is surfacing PR activity in Slack so reviews don't stall. \
                Internal eng team, around 15 people. We run a long-running Node.js \
                service on Fly.io and have Redis available there. Per-repo allowlist \
                routing each repo to one channel. Events we care about: opened, \
                ready_for_review, closed. Crash-safety and retries are required -- \
                no in-memory-only queues. Config via a single YAML file at startup, \
                no hot reload. Out of scope: two-way interaction, review assignment, \
                backfill, config UI.\
            """),
            "Go with your recommendation. Walk me through the design.",
            "Looks good, keep going.",
            "Design is approved. Write the spec.",
            "Spec looks good. Nothing else for now.",
        ],
        setup=skill_setup("scope", project_root),
        cleanup=cleanup_globs("references/specs/2026-*-github-webhook*.md"),
    )
