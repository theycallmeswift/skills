# claude-cloud-orchestrator — eval record

Recorded 2026-10-11 from `iteration_01`: benchspec 0.0.5, Docker sandbox, Claude Code 2.1.296 in the guest, sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=claude-cloud-orchestrator EVAL_ARGS='--count 3 -n 3'`. The activation line (`Skill … invoked`) is scoped off baseline and excluded from these tallies; the skill fired in 3 of 3 trial cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| report-routine-is-deleted | 4/12 (33%) | 12/12 (100%) | +67pp |
| **Headline** (mean of per-sample rates) | **33%** | **100%** | **+67pp** (noise band ±8pp) |

No routing evals yet.

## Notes

**What the skill fixes.** A worker's report fires into the orchestrator through a Routine; once handled, the report Routine and the wake Routine it answers should be deleted. `delete_trigger`'s description warns that deleting a Routine deletes every session it started, which doesn't apply to a Routine bound to an existing session, but a bare agent reads it as a threat to the worker or to itself.

- **Baseline (0 of 3 deleted either Routine).** Two samples listed the Routines, then stopped and asked, saying deletion "could remove the worker session" or "could delete this session". The third made no tool call at all and offered to delete the wake Routine if asked.
- **Trial (3 of 3).** Every sample deleted `trig_01HZREPORT42` and `trig_01HZWAKE42`, left PR #41's report alone, and claimed nothing about sessions.

The pass on "no delete of PR #41's Routine" is free on baseline, since it deleted nothing; the lift is in the two delete lines and the session claim.

**Fake.** The Routine tools come from `evals/support/fake-claude-code-remote/`, a stdlib MCP server registered in `setup.sh` on both arms. The guest has no `python3`, so `setup.sh` installs it first. The tool descriptions are copied from the live server, with `delete_trigger`'s warning verbatim; that text is what the baseline balks at.

**Ported from MechaSwift.** The scenario was first run there on 2026-10-05 (`claude-opus-5-5`): baseline 67%, skill 100%. Its baseline could read the skill from the repository mount and one sample did; here the trial arm alone loads it.
