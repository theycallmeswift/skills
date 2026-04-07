# Skill Evals

How we test skills and project rules in MechaSwift.

## Running

```bash
make test                              # all suites
make test ARGS="ghostwrite"            # one suite
make test ARGS="--no-baseline scope"   # skip baseline runs (faster)
make test ARGS="--verbose"             # show passing assertion evidence too
```

The harness discovers eval files under `tests/`, runs each case in parallel through the Claude Agent SDK (concurrency cap 4), grades with an LLM judge, and prints a live table (TTY) or pytest dots (CI).

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
      "prompt": "...",
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
- `files` — relative paths from the eval file dir; copied into the run's temp cwd.
- `grader_model` — optional, defaults to Haiku. Override for subjective skills like ghostwrite.
- `assertions` — graded by an LLM judge (one call per run). Be specific.
- `cleanup` — optional glob patterns deleted after the run.

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
