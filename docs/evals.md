# Skill Evals

How we test skills and project rules in MechaSwift.

## Running

```bash
make test                                                        # all suites
make test ARGS="ghostwrite"                                      # one suite
make test ARGS="--no-baseline scope"                             # skip baseline runs (faster)
make test ARGS="--verbose"                                       # show passing assertion evidence too
make test ARGS="--model claude-haiku-4-5-20251001"               # run the agent on a specific model
```

The harness discovers eval files under `tests/`, runs each case in parallel through the Claude Agent SDK (concurrency cap 8), grades with an LLM judge, and prints a live table (TTY) or pytest dots (CI).

`--model` overrides the model the agent uses for the run. Useful for baselining against a cheaper/weaker model (e.g. Haiku) to separate real skill value from model-capability freebies — if a case passes on both the with-skill and baseline variants on a weak model, the skill isn't doing any work.

## Layout

- `tests/skills/<name>/evals.json` — skill quality evals. Each case is tagged `lift` or `regression` (see Tiers below). Lift cases run twice (with-skill and baseline) so the suite can measure delta; regression cases run only with-skill.
- `tests/core/<name>.json` — core evals. Single run per case in a temp cwd seeded with `AGENTS.md`. The agent discovers skills on its own. Used for global rules (e.g. `no-ai-attribution`) and the `skill-triggers` discovery test.
- `tests/support/harness/` — the Python harness itself. Has its own pytest unit tests (`uv run pytest tests/support`).

## Eval file format

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "tier": "lift",
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
- `tier` — `lift` or `regression` (default `regression`). See Tiers below.
- `turns` — **required**. List of user messages, sent sequentially. Single-turn cases use a one-element list. Multi-turn cases script each reply in order.
- `files` — relative paths from the eval file dir; copied into the run's temp cwd.
- `grader_model` — optional, defaults to Haiku. Override for subjective skills like ghostwrite.
- `assertions` — graded by an LLM judge (one call per run). Be specific.
- `cleanup` — optional glob patterns deleted after the run.

## Tiers

Every skill case is tagged `lift` or `regression`. These tiers answer different questions and have different pass bars. (This mirrors the split Anthropic recommends in "Demystifying evals for AI agents" and the Agent Skills evaluating-skills guide.)

**Lift tier — does this skill still do useful work?**
- Runs the case twice: once with the skill loaded, once as a baseline.
- Reports with-skill, baseline, delta, and a status column (`OK` / `WARN` / `FAIL`).
- Fails the suite only if the with-skill rate drops below 75% or the run errors. A flat or negative delta emits `WARN` but does not fail — single runs have variance, and a saturated case (where even the baseline passes) is informational, not a regression.
- Use for cases where a weaker model fails without the skill and the skill visibly changes behavior. Baseline against Haiku is the fastest way to find real lift: `make test ARGS="--model claude-haiku-4-5-20251001"`.

**Regression tier — did we break anything?**
- Runs the case only with the skill loaded.
- Must hit 100%. Any failed assertion fails the suite.
- Use for cases where the skill encodes a rule the model might drift from (format, tool use, safety rules) but where the base model also currently gets it right. Catches skill edits that silently break format, drift from model upgrades, and anything that matters even if both variants would pass today.

**Graduation:** A lift case whose delta has dropped to zero on every frontier model is a candidate for graduation to the regression tier (or deletion if both variants saturate even on weak models — see "Remove capability freebies" below). A regression case that starts failing on a new model is a lift case again.

**Remove capability freebies:** If a case passes at 100% on both variants on *both* Opus and Haiku, it's testing model capability, not skill value. Delete it (or rewrite the assertion to be harder). Keeping it inflates the with-skill pass rate without reflecting anything the skill does.

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
    {"text": "Output starts with a clear title for the summarized content"},
    {"text": "Output contains a short summary (1-2 sentences) near the top"}
  ],
  "evals": [
    {"id": "c1", "tier": "regression", "turns": ["..."], "assertions": [{"text": "..."}]}
  ]
}
```

Shared assertions are prepended to each case's own `assertions`. A case can opt out with `"use_shared_assertions": false`.

## Grader input limits

Long multi-turn runs produce huge grader prompts. Defaults: 40,000 chars of stdout, 10,000 chars per file, last 50 tool trace entries. Override per case with `"grader_input_limit": 80000` (scales all three).

## Cleanup safety

`cleanup` globs must be relative paths under `references/specs/` or `tmp/`. Absolute paths, `..` segments, and other roots are rejected at load time.

## Writing good assertions

- **Prefer semantic checks over literal format checks.** "Output contains a short 1-2 sentence summary near the top" is robust; "Output contains the literal heading `## TL;DR`" will fail on perfectly valid outputs that use `**Summary:**` or a different heading. Only pin to literal form when a downstream consumer actually parses that form.
- **Grade the outcome, not the path.** If the user cares that a summary has five components, assert the five components, not the tool sequence that produced them. Brittle structural checks are the single biggest source of false failures (Anthropic's CORE-Bench anecdote: rigid grading scored Opus at 42%; semantic grading scored it at 95%).
- **Testable, observable properties.** "Output uses Swift's voice" is too soft. "Output contains no em dashes" is graded reliably.
- **Anchor at least half of assertions in content, not form.** A case that only grades headings can pass with a nonsense body.
- **Use deterministic assertions for tool use.** `tool_called` / `tool_not_called` / `skill_invoked` are cheaper, faster, and not subject to grader variance.
- **Multi-turn replies are static.** If the script's turn 3 reply is written assuming turn 2 asks a specific question and the model asks a different one, the reply is a non-sequitur. Keep scripted replies broad, or split the case into single-turn variants.

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
tmp/evals/2026-04-08T14-30-00/
  ghostwrite/
    eval-sponsor-email/               # lift case — both variants
      with_skill/outputs/output.md
      with_skill/grading.json
      baseline/outputs/output.md
      baseline/grading.json
      eval_metadata.json
  summarize/
    eval-devto-top-article/           # regression case — with-skill only
      with_skill/outputs/output.md
      with_skill/grading.json
      eval_metadata.json
  _core/
    no-ai-attribution/
      eval-throwaway-commit/run/...
```

`tmp/` is gitignored.

## Writing good evals

- At least 3 cases per skill: happy path, edge case, adversarial/negative.
- Decide the tier up front. If the skill should visibly change behavior on this input, tag `lift`. If the skill encodes a rule you want to protect against drift but the base model also gets it right, tag `regression`.
- Assertions describe observable properties of the output, not subjective vibes. The grader is an LLM judge; "Output uses Swift's voice" is too soft. "Output contains no em dashes" is graded reliably.
- Baseline new lift cases against Haiku before merging: `make test ARGS="--model claude-haiku-4-5-20251001 <skill>"`. If both variants tie at 100% on Haiku, the case isn't measuring skill value — rewrite the assertion or drop it.
- Skill triggers: keep `tests/core/skill-triggers.json` updated when you add a skill.

## Adding a new skill

1. Create `tests/skills/<name>/evals.json` with at least 3 cases.
2. Add a case to `tests/core/skill-triggers.json` that prompts a realistic trigger and asserts the Skill tool fires.
3. `make test ARGS="<name>"` to verify.
