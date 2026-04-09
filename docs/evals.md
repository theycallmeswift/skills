# Evals

Two commands, two questions.

## `make test` — Did I break anything?

Fast, deterministic, runs on every edit. Target <90s. No LLM grading.

```
make test                    # all suites
make test ARGS="ghostwrite"   # single suite
```

Every assertion grades in Python. If your eval uses a check that can't be expressed deterministically, it belongs in the rubric (see `make eval`).

## `make eval` — Is the skill still doing good work?

Deep, rubric-graded, runs pre-release or when iterating on a skill. Target ~2 min.

```
make eval                    # all suites (with lift baselines)
make eval ARGS="summarize"   # one suite
```

## Writing an eval

1. Create `tests/<name>.json`. If `<name>` matches a directory under `skills/`, the harness treats it as a skill suite; otherwise it's a core suite.
2. Each case has `id`, `turns`, and `assertions` (an array of deterministic primitives). Optional: `intent` (`lift` or `regression`), `files`, `cleanup`.
3. For skill suites that want quality grading in `make eval`, create `skills/<name>/RUBRIC.md` with `## Critical` and `## Optional` sections.

## Assertion vocabulary

See `references/specs/2026-04-08-eval-harness-plan-b-design.md` for the full list of primitives across content, shape, trace, files, and the `script_name` escape hatch.

## Rubric format

```markdown
# <Skill> Rubric

## Critical

- <testable outcome the output must satisfy>

## Optional

- <nice-to-have; reported but never fails the case>
```

The grader returns `pass` / `fail` / `n/a` for each item. A case fails only if a critical item is `fail`. `n/a` is for items that legitimately don't apply (e.g. a refusal case).

## Fixtures

Put shared input files under `tests/fixtures/`. Reference them in a case via `"files": ["fixture-name.ext"]`.

## Artifacts

Every run writes artifacts under `tmp/evals/<timestamp>/` — one directory per suite/case/variant with the raw output, files written, and grading results.
