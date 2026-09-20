#!/usr/bin/env python3
"""
Delegate implementation and review tasks to `codex exec` as background jobs.

Builds every `codex exec` call, keeps job state outside the repo, and reports the
final message plus token usage. Codex only edits the worktree; the caller commits.
The logic lives in the codexrun package beside this file.

Usage:
    codex_run.py preflight
    codex_run.py start {implement|review} --effort EFFORT [--model M] [--tier T] [--network]
        [--brief F] [--context F] [--risks F] [--rules F] [--report F] [--base REF]
        [--resume JOB_ID] [--cd DIR] [--wait]
    codex_run.py status [--all] [--json]
    codex_run.py result [JOB_ID|last] [--json]
    codex_run.py cancel JOB_ID

Exit codes: 0 ok; 1 job failed or cancelled; 2 usage or input error; 3 preflight failed;
4 job still running.
"""

from __future__ import annotations

import sys

from codexrun.cli import main

if __name__ == "__main__":
    sys.exit(main())
