# Eval Harness Overhaul

**Date:** 2026-04-07
**Status:** Draft

## Goal

Replace the current `/eval` Claude Code workflow with a deterministic Python harness that runs MechaSwift's skill and core evals in parallel from the terminal. Fixes three problems with today's setup: (1) the orchestrator is a Claude Code session that can't spawn nested subagents, blocking skills that themselves dispatch agents; (2) eval files are scattered across `skills/*/evals/` and `evals/` with no unified structure; (3) there is no live, rspec/pytest-style visualization while tests run.

## Non-Goals

- Adopting a third-party eval framework (Inspect AI, Promptfoo, DeepEval). Researched and rejected — all are either too heavy, prompt-shaped not agent-shaped, or don't ship a coding-agent CLI provider.
- Trigger-eval optimization (skill description tuning). Stays in skill-creator land.
- HTML report viewer with human feedback capture. Out of scope for v1; can be added later if needed.
- Multi-agent execution today. Codex / Gemini / Aider runners are stubbed (`NotImplementedError`) for future use.
- Production deployment / CI integration. Local-first; CI can come later.

## Approach

A small Python package under `tests/support/harness/` orchestrates eval runs as plain subprocess work via the Claude Agent SDK. The orchestrator runs from the terminal (not from inside Claude Code), so each skill run is a fresh top-level Claude session that can spawn subagents normally. Eval files live under a top-level `tests/` tree mirroring the project structure (`tests/skills/<name>/evals.json`, `tests/core/<name>.json`). A `make test` target invokes the harness via `uv`. Live results render through `rich` in a TTY and pytest-style dots in CI.

The runner is skill-agnostic: it copies a list of context paths into a temp cwd and runs a prompt. The discovery layer is the only place that knows about skills, baseline runs, and core evals — it assembles `context_paths` and the prompt for each run case.

Two alternatives were considered and rejected:
- **Inspect AI** — heavier framework, more concepts to learn, overkill for ~12 cases.
- **Claude-only Agent SDK** — locks us in. Multi-agent stub costs almost nothing now and future-proofs against running the same eval against Codex/Gemini.

## Components

```
mechaswift/
├── Makefile                                # `make test ARGS="..."`
├── pyproject.toml                          # uv-managed; deps: claude-agent-sdk, rich
├── tests/
│   ├── support/
│   │   └── harness/
│   │       ├── __init__.py
│   │       ├── __main__.py                 # CLI entry: arg parsing, dispatch, exit code
│   │       ├── discovery.py                # walks tests/ tree, builds run plans
│   │       ├── runner.py                   # RunResult + run_claude / run_codex(stub) / run_gemini(stub)
│   │       ├── grader.py                   # LLM-judge per run, structured JSON output
│   │       └── reporter.py                 # RichReporter (TTY) + DotsReporter (CI), auto-detect
│   ├── skills/
│   │   ├── ghostwrite/evals.json
│   │   ├── scope/evals.json
│   │   ├── summarize/evals.json
│   │   └── prompt-engineer/evals.json
│   └── core/
│       ├── no-ai-attribution.json
│       └── skill-triggers.json             # NEW: one case per skill, verifies discovery path
└── tmp/evals/<ISO-timestamp>/              # run artifacts, gitignored
```

Deletions on landing:
- `.claude/commands/eval.md`
- `evals/` (contents moved to `tests/core/`)
- `skills/*/evals/` (contents moved to `tests/skills/<name>/evals.json`)
- `docs/evals.md` rewritten to document the new harness

## Data / Interfaces

### Eval file format

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "prompt": "Rewrite this email in Swift's voice: ...",
      "files": ["fixtures/raw-email.md"],
      "grader_model": "claude-haiku-4-5-20251001",
      "assertions": [
        { "text": "Output preserves all factual claims from the source" },
        { "text": "Output does not use the word 'leverage'" }
      ],
      "cleanup": []
    }
  ]
}
```

- `name` — replaces today's `skill_name` / `eval_name`. Used for filtering via positional args.
- `id` — slug string (not integer). Used in artifact paths and CLI filtering.
- `files` — relative paths from the eval file dir; copied into the run's temp cwd.
- `grader_model` — optional, defaults to Haiku. Override per case for subjective skills.
- `assertions[].text` — graded by LLM judge. No `type` field for now; add back if/when we split graders.
- `cleanup` — optional glob patterns deleted after the run finishes.

Type (skill vs core) is inferred from path: `tests/skills/*` → skill eval, `tests/core/*` → core eval.

### Runner interface

```python
@dataclass
class RunResult:
    stdout: str
    files_written: dict[str, str]   # path → content, relative to cwd, only new/modified
    input_tokens: int
    output_tokens: int
    duration_s: float
    exit_code: int
    tool_trace: list[dict]           # [{name: "Skill", input: {skill: "ghostwrite"}}, ...]

async def run_claude(
    prompt: str,
    cwd: Path,
    context_paths: list[Path],       # files or dirs, copied into cwd preserving relative structure
    timeout_s: float = 300,
) -> RunResult: ...

async def run_codex(...) -> RunResult: raise NotImplementedError
async def run_gemini(...) -> RunResult: raise NotImplementedError
```

The runner is skill-agnostic. Discovery assembles `context_paths` and the prompt:

| Run kind | `context_paths` | Prompt |
|---|---|---|
| Skill with-skill | `[skills/<name>/, AGENTS.md, *eval.files]` | `"Before responding, read and follow skills/<name>/SKILL.md.\n\n" + eval.prompt` |
| Skill baseline | `[AGENTS.md, *eval.files]` | `eval.prompt` |
| Core | `[AGENTS.md, *eval.files]` | `eval.prompt` |

Notes:
- AGENTS.md is the canonical project context file. CLAUDE.md is a symlink to it; the harness resolves the symlink.
- Tool trace is extracted from the SDK message stream (`ToolUseBlock` events). Replaces today's "ask the subagent to append a Tool Trace section" hack — can't be forgotten or faked.
- Token usage comes from the SDK's final result message.
- Each run gets a fresh `tempfile.mkdtemp()` cwd. After the run, the harness walks the dir and captures any new/modified files into `files_written`.

### Grader interface

```python
@dataclass
class Grading:
    expectations: list[dict]   # [{text, passed, evidence}, ...]
    passed: int
    failed: int
    total: int

async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str = "claude-haiku-4-5-20251001",
) -> Grading: ...
```

- One grader call per run (not per assertion). Grader sees the full output and grades all assertions in a single structured response.
- Uses Claude Agent SDK's structured `output_format` with a JSON schema matching `Grading`. No regex parsing.
- Grader prompt embeds the existing PASS/FAIL rubric: clear evidence required, fail on uncertainty, no partial credit.
- Each grader call is parallelized via the same `asyncio.Semaphore` as runner calls (cap 4).

### Reporter interface

```python
class Reporter(Protocol):
    def start(self, total: int) -> None: ...
    def case_started(self, case_id: str) -> None: ...
    def case_finished(self, case_id: str, result: CaseResult) -> None: ...
    def finish(self) -> None: ...

def make_reporter() -> Reporter:
    return RichReporter() if sys.stdout.isatty() else DotsReporter()
```

- **RichReporter** — `rich.live.Live` wrapping a `rich.table.Table`. Columns: Suite, Case, Status, Duration, Tokens, Pass Rate. Spinner on in-progress rows. Color: green pass, red fail, yellow partial.
- **DotsReporter** — `.` / `F` / `E` per case, newline every 50, summary table at the end.
- **Final summary** matches today's `/eval` shape: skill eval table with With/Baseline/Delta columns, core eval table with single Result column, failures section with assertion text + evidence.

### CLI

```
uv run python -m tests.support.harness [names...] [--verbose] [--no-baseline]
```

- **names** (positional, optional) — filter by `name` field. No args = run everything.
- **`--verbose`** — print evidence for passing assertions, not just failures.
- **`--no-baseline`** — skip baseline runs for skill evals. Faster iteration.

Exit code 0 if all assertions pass (skill with-skill runs + core runs); 1 otherwise. Baseline failures don't affect exit code.

### Makefile

```makefile
.PHONY: test

test:
	uv run python -m tests.support.harness $(ARGS)
```

Usage: `make test`, `make test ARGS="ghostwrite --verbose"`, `make test ARGS="--no-baseline scope"`.

### Artifacts

```
tmp/evals/2026-04-07T14-30-00/
  ghostwrite/
    eval-sponsor-email/
      with_skill/
        outputs/output.md
        eval_metadata.json
        grading.json
      without_skill/
        outputs/output.md
        eval_metadata.json
        grading.json
  scope/
    ...
  _core/
    skill-triggers/
      eval-ghostwrite-triggers-on-rewrite/
        run/outputs/output.md
        eval_metadata.json
        grading.json
    no-ai-attribution/
      eval-throwaway-commit/
        run/...
```

`tmp/` is gitignored. Each run is timestamped so prior runs are preserved for diffing.

## Testing

How we know the harness works:

- **Self-bootstrap** — run `make test` against the migrated eval files. All previously-passing skill evals should still pass at parity (or better, since baseline isolation is now real). Any regression is a migration bug, not a harness bug.
- **Skill triggers eval** — `tests/core/skill-triggers.json` has one case per skill. Each case prompts something the skill should fire on, asserts the Skill tool was invoked with the expected name, and asserts the output is on-task. Verifies the discovery path (AGENTS.md loaded, skills discoverable) end-to-end.
- **Manual checks during build:** parallelism cap holds under load, temp cwds get cleaned up on success and on failure, tool trace captures Skill invocations correctly, grader structured output matches the schema, reporter renders correctly in both TTY and piped modes.
- **Left unverified** — Codex / Gemini stubs (they raise `NotImplementedError`); HTML viewer (out of scope).

## Open Questions

None at spec time. Items to resolve during implementation:

- **Implicit CLAUDE.md dependence in current evals.** Some existing eval cases may have implicitly depended on the project `CLAUDE.md` being in scope. Migration step: re-run each migrated eval and confirm parity. If a case regresses because it needed AGENTS.md context that isn't being copied, either add it to that case's `files` or fix the eval prompt to be self-contained.
- **Skill loading via prompt preamble.** The "Before responding, read and follow skills/<name>/SKILL.md" preamble matches today's `/eval` behavior. If the Agent SDK gains a first-class skill-loading API, swap to it.
- **Concurrency cap of 4.** Starting value based on researcher recommendation for per-account rate limits. Tune if we hit 429s or if runs are unnecessarily serial.
