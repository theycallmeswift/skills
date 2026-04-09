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

Every assertion is a JSON object with exactly one primitive key.

**Content** (checked against `final_message` by default; override with `"on": "stdout"` or `"on": "files.<glob>"`):

| Primitive | Example | Passes when |
|---|---|---|
| `regex` | `{"regex": "\\?", "min": 1, "max": 2}` | Match count is within `[min, max]`. Defaults: `min=1`, `max=∞`. |
| `not_regex` | `{"not_regex": "(?i)sorry"}` | Zero matches. |
| `contains` | `{"contains": "42"}` | Literal substring found. |
| `contains_all` | `{"contains_all": ["A", "B"]}` | Every literal found. |
| `not_contains` | `{"not_contains": "secret"}` | Literal absent. |

**Shape:**

| Primitive | Example | Passes when |
|---|---|---|
| `output_len_lte` | `{"output_len_lte": 600}` | Character count ≤ value. |
| `output_len_gte` | `{"output_len_gte": 100}` | Character count ≥ value. |
| `token_usage_lte` | `{"token_usage_lte": 50000}` | `input + output` tokens ≤ value. |

**Trace:**

| Primitive | Example | Passes when |
|---|---|---|
| `tool_called` | `{"tool_called": "scrape_as_markdown"}` | Tool name appears in trace (substring match). |
| `tool_not_called` | `{"tool_not_called": "WebFetch"}` | Tool name absent from trace. |
| `skill_invoked` | `{"skill_invoked": "ghostwrite"}` | `Skill` tool fired with matching skill (bare or prefixed). |
| `skill_not_invoked` | `{"skill_not_invoked": "ghostwrite"}` | No matching `Skill` tool invocation. |
| `trace_order` | `{"trace_order": ["Read", "Write"]}` | Tools appear in trace in this order (gaps ok). |
| `trace_count_lte` | `{"trace_count_lte": {"tool": "Bash", "n": 3}}` | Tool invocation count ≤ `n`. |
| `turn_count_lte` | `{"turn_count_lte": 1}` | Agent completed in ≤ `n` turns. |

**Files:**

| Primitive | Example | Passes when |
|---|---|---|
| `files_written_include` | `{"files_written_include": "refs/specs/*.md"}` | At least one written file matches glob. |
| `files_written_exclude` | `{"files_written_exclude": "package.json"}` | No written file matches glob. |
| `files_written_count` | `{"files_written_count": 0}` | Exact file count. |
| `file_contains` | `{"file_contains": {"path": "*.md", "text": "X"}}` | A file matching `path` glob contains `text` or matches `regex`. Set exactly one of `text` or `regex`. |

**Script:**

| Primitive | Example | Passes when |
|---|---|---|
| `script_name` | `{"script_name": "ghostwrite"}` | `skills/<name>/lint.py` exits 0 on the output. |

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
