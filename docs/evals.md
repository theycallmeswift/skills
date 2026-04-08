# Skill Evals

How we test skills and project rules in MechaSwift.

## Running

```bash
make test                              # all suites
make test ARGS="ghostwrite"            # one suite
make test ARGS="--no-baseline scope"   # skip baseline runs (faster)
make test ARGS="--verbose"             # show passing assertion evidence too
```

The harness discovers eval files under `tests/`, runs each case in parallel through the Claude Agent SDK (concurrency cap 8), grades with an LLM judge, and prints a live table (TTY) or pytest dots (CI).

## Layout

- `tests/skills/<name>/evals.json` — skill quality evals. Each case runs twice: once with the skill loaded (preamble + skill dir copied into the temp cwd), once as a baseline. The summary reports both and the delta.
- `tests/core/<name>.json` — core evals. Single run per case in a temp cwd seeded with `AGENTS.md`. The agent discovers skills on its own. Used for global rules (e.g. `no-ai-attribution`) and the `skill-triggers` discovery test.
- `tests/support/harness/` — the Python harness itself. Has its own pytest unit tests (`uv run pytest tests/support`).

## Eval file format

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "turns": ["..."],
      "files": [],
      "grader_model": "claude-haiku-4-5-20251001",
      "assertions": [
        { "text": "Output preserves all factual claims" }
      ],
      "cleanup": []
    }
  ]
}
```

- `name` — used for filtering on the CLI.
- `id` — slug, used in artifact paths and surfaced in the summary.
- `turns` — **required**. List of user messages, sent sequentially. Single-turn cases use a one-element list. Multi-turn cases script each reply in order.
- `files` — relative paths from the eval file dir; copied into the run's temp cwd.
- `grader_model` — optional, defaults to Haiku. Override for subjective skills like ghostwrite.
- `assertions` — graded by an LLM judge (one call per run). Be specific.
- `cleanup` — optional glob patterns deleted after the run.

## Assertion types

Assertions are graded in two ways depending on their shape.

**Text assertions** (default) go to an LLM judge:
```json
{"text": "Output contains a '## TL;DR' section"}
```

**Deterministic assertions** are graded in Python against the tool trace — faster, cheaper, no LLM variance:
```json
{"tool_called": "scrape_as_markdown"}
{"tool_not_called": "WebFetch"}
{"skill_invoked": "ghostwrite"}
```

Use deterministic assertions for any observable fact about tool use. Reserve text assertions for content and behavior.

## Shared assertions

Cases in the same suite often share structural assertions (e.g. every summarize case wants the same H1/TL;DR/Cliff Notes format). Hoist them to the suite level:

```json
{
  "name": "summarize",
  "shared_assertions": [
    {"text": "Output contains an H1 title"},
    {"text": "Output contains a '## TL;DR' section"}
  ],
  "evals": [
    {"id": "c1", "turns": ["..."], "assertions": [{"text": "..."}]}
  ]
}
```

Shared assertions are prepended to each case's own `assertions`. A case can opt out with `"use_shared_assertions": false`.

## Grader input limits

Long multi-turn runs produce huge grader prompts. Defaults: 40,000 chars of stdout, 10,000 chars per file, last 50 tool trace entries. Override per case with `"grader_input_limit": 80000` (scales all three).

## Cleanup safety

`cleanup` globs must be relative paths under `references/specs/` or `tmp/`. Absolute paths, `..` segments, and other roots are rejected at load time.

## Writing good assertions

- **Prefer testable, observable properties.** "Output contains `## TL;DR`" is gradable; "output is well-structured" is not.
- **Avoid surface-only checks** (character counts, backtick counts, exact whitespace) unless they are load-bearing.
- **Anchor at least half of assertions in content, not form.** A case that only grades headings can pass with a nonsense body.
- **Multi-turn replies are static.** If the script's turn 3 reply is written assuming turn 2 asks a specific question and the model asks a different one, the reply is a non-sequitur. Keep scripted replies broad, or split the case into single-turn variants (one for process, one for content).

## Multi-turn cases

Skills with conversational flows (e.g. `scope`, which asks one clarifying question at a time) need more than one turn to reach a graded state. Add them by listing each reply in `turns`:

```json
{
  "id": "github-webhook-slack",
  "turns": [
    "Scope a GitHub webhook -> Slack PR summaries service.",
    "Purpose: surface PR activity so reviews don't stall. Internal eng team, ~15 people.",
    "Node.js service on Fly.io, Redis is available.",
    "Go with your recommendation.",
    "Design looks good. Write the spec.",
    "Spec looks good."
  ],
  "assertions": [...]
}
```

Notes:
- Replies are **static**. If the agent asks something the script didn't anticipate, the reply may be a non-sequitur — assertions grade the final trajectory, not conversational coherence. Keep replies broad enough to be plausible answers regardless of exact question phrasing.
- The whole session shares one 300s timeout.
- `output.md` contains every assistant turn concatenated with `--- turn N ---` separators.
- Token counts are summed across turns.

## Artifacts

Every run writes to `tmp/evals/<ISO-timestamp>/`:

```
tmp/evals/2026-04-07T14-30-00/
  ghostwrite/
    eval-sponsor-email/
      with_skill/outputs/output.md
      with_skill/grading.json
      without_skill/outputs/output.md
      without_skill/grading.json
      eval_metadata.json
  _core/
    no-ai-attribution/
      eval-throwaway-commit/run/...
```

`tmp/` is gitignored.

## Writing good evals

- At least 3 cases per skill: happy path, edge case, adversarial/negative.
- Assertions describe observable properties of the output, not subjective vibes. The grader is an LLM judge; "Output uses Swift's voice" is too soft. "Output contains no em dashes" is graded reliably.
- Skill triggers: keep `tests/core/skill-triggers.json` updated when you add a skill.

## Adding a new skill

1. Create `tests/skills/<name>/evals.json` with at least 3 cases.
2. Add a case to `tests/core/skill-triggers.json` that prompts a realistic trigger and asserts the Skill tool fires.
3. `make test ARGS="<name>"` to verify.
