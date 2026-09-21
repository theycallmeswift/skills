#!/usr/bin/env python3
"""
Delegate implementation and review tasks to `codex exec` as background jobs.

Builds every `codex exec` call, keeps job state outside the repo, and reports the
final message plus token usage. Codex only edits the worktree; the caller commits.
The logic lives in the agentrun package beside this file.

Usage:
    agent_run.py preflight
    agent_run.py start --effort EFFORT [--template implement|review|FILE] [--model M] [--tier T]
        [--brief F] [--context F] [--risks F] [--rules F] [--report F]
        [--sandbox read-only|workspace-write] [--schema [FILE]] [--diff] [--base REF]
        [--network] [--resume JOB_ID] [--gate CMD] [--cd DIR] [--wait]
    agent_run.py status [--all] [--json]
    agent_run.py result [JOB_ID|last] [--json]
    agent_run.py cancel JOB_ID

Exit codes: 0 ok; 1 job failed or cancelled; 2 usage or input error; 3 preflight failed;
4 job still running; 5 the gate failed or could not run.
"""

from __future__ import annotations

import sys

from agentrun.cli import main

if __name__ == "__main__":
    sys.exit(main())
