# Eval Harness Plan B: Two-Tier Refactor

**Date:** 2026-04-08
**Status:** Draft
**Branch:** `eval-harness-refactor`

## Goal

Refactor the eval harness so it reliably answers two different questions with two different tools:

1. **"Did we break anything?"** — fast, deterministic, runs on every edit. Target <90s.
2. **"Is the skill still doing good work?"** — deep, rubric-graded, runs pre-release or when iterating on a skill. Target ~2 min.

Fixes five concrete pain points with today's harness:

1. **Brittle** — ~60% of assertions are free-form LLM-judged prose (`"Output contains a greeting 'Hey, Sarah --'"`). Grader variance and scripted multi-turn replies make real failures hard to distinguish from noise.
2. **Confusing UI** — one table mixes core / regression / lift with a three-state (WARN/OK/FAIL) lift status whose semantics are non-obvious. Baseline rows are shown inline.
3. **Slow** — lift cases run twice per pass, every case goes through a full Agent SDK session plus a Haiku grader call, and there's no tier separation so every run is "the deep one."
4. **No model-perf signal** — `--model` overrides one model at a time; there's no report showing which assertions pass on which models.
5. **Tests cause skill bloat** — prose assertions like `"Output contains a 'Technique:' line"` reward skills that encode that exact structure. Skills grow rules to pass evals, not to be better.

## Non-Goals

- **Model matrix.** Reserved as a `--models=...` flag but not built in v1. The architecture supports it (add a model dimension to `RunPlan`), but MVP runs a single model per command. The report shows which model was used.
- **Third-party eval frameworks.** Still inside `tests/support/harness/`. No Inspect AI, Promptfoo, etc.
- **HTML report / web UI.** Terminal only.
- **Caching / incremental runs.** Every invocation runs every case. Cache layers can come later.
- **Saturated cases as hard failures.** They emit WARN in v1. Promote to FAIL once the detection logic is proven.
- **CI integration.** Local-first. CI can adopt `make test` when ready.

## Current State

The harness is well-built but optimized for the wrong thing: "many LLM-judged assertions per case," which is exactly the source of all five pain points.

```
tests/
├── skills/
│   ├── ghostwrite/evals.json        (2 cases, 11 text assertions + 1 lint)
│   ├── summarize/evals.json         (6 cases, 20+ text + 6 shared lint)
│   ├── scope/evals.json             (3 cases, 23 text)
│   └── prompt-engineer/evals.json   (3 cases, 20 text)
├── core/
│   ├── skill-triggers.json          (6 cases, deterministic-heavy)
│   └── no-ai-attribution.json       (3 cases, text assertions)
└── support/harness/                 (runner, grader, discovery, reporter, orchestrator)
```

A `make test` runs ~28 runs (23 skill cases — 5 lift × 2 variants + 18 regression × 1 — plus 9 core cases). Every case grades via a Haiku LLM judge with a verbose prompt (stdout + files + tool trace). The `Rich` reporter shows all three suite kinds in one table with WARN/OK/FAIL statuses.

## Approach

Split the harness into two tiers behind two commands. Both share the same runner, discovery, and orchestrator — the split is in *what gets graded and what gets reported*, not in the execution engine.

### Two tiers

| | `make test` (fast) | `make eval` (deep) |
|---|---|---|
| **Purpose** | "Did I break anything obvious?" | "Is the skill still doing good work?" |
| **Runs per case** | 1 (with-skill only) | 1 per case + 1 baseline per lift case |
| **Default model** | `claude-haiku-4-5` (runner) | `claude-sonnet-4-6` (runner) |
| **Grader** | None — deterministic assertions only | Haiku, via structured rubric output |
| **Rubric grading** | Skipped | One structured call per case |
| **Lift analysis** | No baselines | Yes |
| **Target runtime** | <90 seconds | ~2 minutes |
| **Reporter** | Single table, failures only | Tiered tables (Core / Regression / Lift), includes judge pass rate |

### Two key shifts

1. **The assertion vocabulary gets richer, deterministic, and replaces most text assertions.** 18 primitives covering content, shape, trace, and files, plus one escape-hatch (`script_name`) for checks too complex to express as data. Total: 19.

2. **Quality checks move out of eval files and into per-skill `RUBRIC.md` files.** The skill owns its definition of good. `make eval` loads the rubric and sends it to the grader LLM in one structured call per case. Rubric items are pass / fail / n/a.

These two shifts together address all five pain points:

| Pain | Fix |
|---|---|
| Brittle | Fast tier has zero LLM variance. Deep tier's grader is structured, not free-form. |
| Confusing UI | Tier split = separate commands, separate reporters, no mixed tables. |
| Slow | Fast tier has no baselines, no LLM calls, Haiku runner. |
| No model-perf signal | Deferred, but model name appears in every report header. Future `--models=` flag slots in cleanly. |
| Skill bloat | Rubric lives with the skill, describes goals not form. Form-rule assertions get deleted. |

## Components

### Directory layout (after flattening)

```
mechaswift/
├── Makefile                      # make test + make eval targets
├── skills/
│   ├── ghostwrite/
│   │   ├── SKILL.md
│   │   ├── lint.py               # (existing, still used as skill self-check)
│   │   ├── lint_test.py          # moved from tests/skills/ghostwrite/test_lint.py
│   │   └── RUBRIC.md             # NEW
│   ├── summarize/
│   │   ├── SKILL.md
│   │   ├── lint.py
│   │   ├── lint_test.py
│   │   └── RUBRIC.md             # NEW
│   ├── scope/
│   │   ├── SKILL.md
│   │   └── RUBRIC.md             # NEW
│   └── prompt-engineer/
│       ├── SKILL.md
│       └── RUBRIC.md             # NEW
├── tests/
│   ├── ghostwrite.json           # moved from tests/skills/ghostwrite/evals.json
│   ├── summarize.json            # moved
│   ├── scope.json                # moved
│   ├── prompt-engineer.json      # moved
│   ├── skill-triggers.json       # moved from tests/core/
│   ├── no-ai-attribution.json    # moved from tests/core/
│   ├── fixtures/
│   │   └── test-paper.pdf        # moved from tests/skills/summarize/
│   └── support/
│       └── harness/              # (unchanged location)
│           ├── __main__.py
│           ├── discovery.py      # new: flat scan + skill/core auto-detection
│           ├── runner.py         # unchanged
│           ├── grader.py         # new: deterministic vocab + rubric grader
│           ├── rubric.py         # NEW: RUBRIC.md parser
│           ├── reporter.py       # new: tier-aware reports
│           └── tests/            # harness unit tests
└── references/specs/
    └── 2026-04-08-eval-harness-plan-b-design.md  # this file
```

**Discovery rule:** every `tests/*.json` is an eval suite. If the filename stem matches a directory under `skills/`, it's a **skill suite**. Otherwise it's a **core suite**. No explicit `kind` field needed.

### Assertion vocabulary (deterministic)

All assertions graded in Python, no LLM calls. Each accepts an optional `on` field (`"stdout"` / `"final_message"` / `"files.<glob>"`). Default is `"final_message"`.

**Content (5):**
- `{"regex": "<pattern>", "min": 1, "max": null, "on": "..."}` — regex appears `min` to `max` times (defaults: min=1, no max)
- `{"not_regex": "<pattern>"}` — shorthand for `{"regex": "<pattern>", "max": 0}`
- `{"contains": "<substr>"}` — literal substring must appear
- `{"contains_all": ["a", "b", "c"]}` — all literals must appear
- `{"not_contains": "<substr>"}` — literal must not appear

**Shape (3):**
- `{"output_len_lte": 600}` — char count
- `{"output_len_gte": 100}`
- `{"token_usage_lte": 10000}` — total tokens for the run (catches prompt bloat regressions directly)

**Trace (7):**
- `{"tool_called": "<name>"}` — unchanged
- `{"tool_not_called": "<name>"}` — unchanged
- `{"skill_invoked": "<skill>"}` — unchanged
- `{"skill_not_invoked": "<skill>"}` — negative of `skill_invoked`; passes when the named skill was never loaded during the run
- `{"trace_order": ["scrape_as_markdown", "Write"]}` — all named tools must fire at least once, and in this relative order (other tool calls may interleave)
- `{"trace_count_lte": {"tool": "Bash", "n": 3}}` — no more than N calls to a tool
- `{"turn_count_lte": 1}` — agent shouldn't need multiple turns

**Files (3):**
- `{"files_written_include": "references/specs/*.md"}` — glob must match at least one written file
- `{"files_written_exclude": "package.json"}` — glob must match zero written files (`"*"` = no files at all)
- `{"file_contains": {"path": "<glob>", "text": "Out of scope"}}` — at least one file matching the glob contains the literal text. Accepts `regex` instead of `text` for pattern matching: `{"file_contains": {"path": "<glob>", "regex": "(?i)out of scope"}}`. Exactly one of `text` / `regex` must be set.

**Escape hatch (1):**
- `{"script_name": "ghostwrite"}` — writes the run's `final_message` to a temp file and invokes `skills/ghostwrite/lint.py <temp_path>`. Passes on exit 0. Stderr on failure is captured as evidence. Future: a dict form for arbitrary script paths: `{"script_name": {"skill": "ghostwrite", "file": "other.py"}}`.

**Total:** 19 assertion types (5 content + 3 shape + 7 trace + 3 files + 1 script).

### Rubric format

`skills/<name>/RUBRIC.md`:

```markdown
# Ghostwrite Rubric

Evaluated by `make eval`. Each item is a testable outcome — not a rule to
encode in the skill, but a goal the output must satisfy.

## Critical

- Output preserves every factual claim from input (numbers, names, dates)
- Output reads in Swift's voice: terse, direct, no corporate filler
- Output leads with the point, not preamble like "I wanted to reach out"
- Output is meaningfully shorter than input — no padding, no repetition

## Optional

- Contractions used where natural (we're, don't, that's)
- Sign-off matches Swift's conventions
```

**Parser rule:** bullets under `## Critical` are must-pass. Bullets under `## Optional` are reported but non-failing. Anything outside those two headers is context the grader LLM sees but isn't parsed into items. Simple and human-editable.

### Rubric grader

One structured LLM call per case, one file read per skill:

```python
def grade_rubric(run: RunResult, rubric_path: Path, model: str) -> RubricResult:
    rubric = rubric_path.read_text()                # whole file, verbatim
    items = parse_rubric_items(rubric)              # [{text, critical}, ...]

    prompt = build_rubric_prompt(run, rubric, items)
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "critical": {"type": "boolean"},
                        "status": {"type": "string", "enum": ["pass", "fail", "n/a"]},
                        "evidence": {"type": "string"}
                    },
                    "required": ["text", "critical", "status", "evidence"]
                }
            }
        }
    }
    # call grader model (Haiku by default), return parsed items
```

**Pass rule:** a case passes the rubric if every critical item returns `status: "pass"` or `status: "n/a"`. Only `status: "fail"` on a critical item fails the case. `n/a` lets the grader excuse items that don't apply to the specific output — useful for negative cases like `linkedin-from-scratch`, where many quality items don't apply because the correct behavior is to refuse.

### Fast tier reporter

```
Running 17 cases on claude-haiku-4-5... (concurrency 8)
.................  17/17

## Core
no-ai-attribution        3/3  ok
skill-triggers           6/6  ok

## Skills
ghostwrite               2/2  ok
summarize                5/6  fail  (devto-rust-tab-orchestrator)
scope                    3/3  ok
prompt-engineer          3/3  ok

22/23 pass (96%) in 00:47 on claude-haiku-4-5

### Failures
summarize > devto-rust-tab-orchestrator
  FAIL regex "^#"
  evidence: first non-empty line is "Key points:" (no H1)
```

One table per suite kind. No WARN, no interleaved baselines, model name in the footer. `--verbose` shows passing assertions too.

### Deep tier reporter

```
Running 28 cases on claude-sonnet-4-6... (concurrency 8)

## Core — sonnet
no-ai-attribution                3/3 checks                             ok
skill-triggers                   6/6 checks                             ok

## Skills (regression) — sonnet
                                 checks     judge (crit)
ghostwrite                       2/2        4/4 items                   ok
summarize                        6/6        18/19 items                 fail
scope                            3/3        11/11 items                 ok
prompt-engineer                  3/3        9/9 items                   ok

## Lift — sonnet
                                 with-skill           baseline              status
ghostwrite > sponsor-email       checks 2/2 judge 4/4  checks 1/2 judge 2/4 ok
ghostwrite > linkedin-scratch    checks 2/2 judge 4/4  checks 2/2 judge 4/4 WARN saturated
scope > vague-notifications      checks 3/3 judge 3/3  checks 0/3 judge 0/3 ok
scope > skip-design              checks 3/3 judge 3/3  checks 1/3 judge 1/3 ok
prompt-engineer > fix-bad-prompt checks 2/2 judge 5/6  checks 1/2 judge 2/6 ok

Fast tier: 22/23 pass
Judge (critical): 22/23 pass (1 item failed in summarize > devto-top-article)
Lift: 4 ok, 1 saturated WARN, 0 regression

Total runtime: 02:07 on claude-sonnet-4-6

### Failures
summarize > devto-top-article (sonnet judge)
  critical FAIL: "Key points reference specific content from the article"
  evidence: "Bullets are generic — no mention of Rust, Chrome tabs, or memory pressure"
```

### Eval file format

**Before** (`tests/skills/ghostwrite/evals.json`):
```json
{
  "name": "ghostwrite",
  "shared_assertions": [{"lint": "ghostwrite"}],
  "evals": [
    {
      "id": "sponsor-email",
      "intent": "lift",
      "turns": ["Rewrite this as an email..."],
      "grader_model": "claude-haiku-4-5-20251001",
      "assertions": [
        {"text": "Output contains a greeting in the format 'Hey, Sarah --'"},
        {"text": "Output leads with the results..."},
        {"lint": "ghostwrite"},
        {"text": "Output contains a sign-off of '- Swift'..."},
        {"text": "Output is significantly shorter than the input..."},
        {"text": "Output preserves all key facts: 450 fellows, 30% increase, 92% recommendation rate"},
        {"text": "Output uses contractions..."}
      ]
    }
  ]
}
```

**After** (`tests/ghostwrite.json`):
```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "intent": "lift",
      "turns": ["Rewrite this as an email..."],
      "assertions": [
        {"script_name": "ghostwrite"},
        {"regex": "^Hey, Sarah --"},
        {"regex": "(- Swift|Happy Hacking,\\s*\\nSwift)\\s*$"},
        {"contains_all": ["450", "30%", "92%"]},
        {"output_len_lte": 600}
      ]
    }
  ]
}
```

**Removed fields:** `shared_assertions`, `grader_model`, `grader_input_limit`, `use_shared_assertions`.

**Rubric wiring:** automatic. `make eval` looks for `skills/<suite_name>/RUBRIC.md`. If present, it grades. If absent, no rubric grading for that suite.

## Rollout

One feature branch (`eval-harness-refactor`, already created), one PR against `dev`. Every harness change is test-driven: write the harness unit test first, watch it fail, implement, watch it pass.

### Step 1 — Harness: deterministic assertion vocabulary

TDD per primitive. For each new assertion type, write a harness unit test under `tests/support/harness/tests/test_grader.py` asserting the grader function produces the right pass/fail + evidence on a given RunResult, then implement.

- `_grade_regex`, `_grade_not_regex`, `_grade_contains`, `_grade_contains_all`, `_grade_not_contains`
- `_grade_output_len_lte`, `_grade_output_len_gte`, `_grade_token_usage_lte`
- `_grade_trace_order`, `_grade_trace_count_lte`, `_grade_turn_count_lte`
- `_grade_files_written_include`, `_grade_files_written_exclude`, `_grade_file_contains`
- Rename `_grade_lint` → `_grade_script_name` (signature unchanged; resolves `skills/<name>/lint.py`)

Update `eval.schema.json` to accept the new assertion shapes. Update the existing schema unit tests (`tests/support/harness/tests/test_discovery.py`) to cover the new shapes.

### Step 2 — Harness: tier split, rubric grader, reporter split

TDD throughout.

**Rubric parser (`tests/support/harness/rubric.py`):**
- Unit test: given a RUBRIC.md with Critical and Optional sections, returns `[{text, critical: bool}, ...]`
- Unit test: missing file returns empty list
- Unit test: malformed headers raise a clear error

**Rubric grader (`tests/support/harness/grader.py::grade_rubric`):**
- Unit test: given a fake RunResult + a 3-item rubric, asserts the grader constructs the right prompt and parses the right output shape
- Unit test: `n/a` items don't count toward critical pass
- Unit test: one critical fail = case fail

**Tier split (`tests/support/harness/__main__.py`):**
- Add `make eval` target in Makefile
- Add `tier: "test" | "eval"` through the orchestrator
- Fast tier: no rubric grading, no baselines, Haiku runner default
- Deep tier: rubric grading when skill has RUBRIC.md, baselines for lift, Sonnet runner default
- CLI unit test: `python -m tests.support.harness --tier eval` vs `--tier test` produces expected plan shapes

**Reporter split:**
- `reporter_fast.py`: single-table, failures only, no WARN
- `reporter_deep.py`: tiered tables (Core / Skills / Lift), checks + judge columns, model name in headers
- Unit tests for both: feed in a list of `CaseResult` fixtures, assert the rendered table matches expected

### Step 3 — Flatten the tests tree

Purely mechanical, no tests to add.

- `git mv tests/skills/<name>/evals.json tests/<name>.json` (4 files)
- `git mv tests/core/<name>.json tests/<name>.json` (2 files)
- `git mv tests/skills/summarize/test-paper.pdf tests/fixtures/test-paper.pdf`
- `git mv tests/skills/<name>/test_lint.py skills/<name>/lint_test.py` (2 files)
- Delete empty `tests/skills/` and `tests/core/`
- Update `discovery.py`: scan `tests/*.json`, auto-detect skill vs core by matching `skills/<name>/`
- Update `files:` field resolution: relative to `tests/fixtures/` instead of eval file dir
- Update `conftest.py` / `pyproject.toml` so pytest still finds `skills/*/lint_test.py`
- Run `make test-harness` to confirm discovery still works

### Step 4 — Migrate cases and write RUBRIC.md files

This is the work driven by **Appendix A** below. For each suite:

1. Apply every row in Appendix A (convert, move, or delete)
2. Write `skills/<name>/RUBRIC.md` aggregating all "Rubric (critical)" and "Rubric (optional)" items from the audit
3. Run `make test` — must pass and come in under 90s
4. Run `make eval` — rubric grading must be green (or failures clearly actionable)

### Step 5 — Docs + cleanup

- Rewrite `docs/evals.md` for new commands, assertion vocabulary, rubric workflow
- Update `AGENTS.md` Commands section (`make test` + `make eval`)
- Update `CLAUDE.md` Commands section
- Delete harness dead code: `shared_assertions` parsing, `use_shared_assertions` field, WARN lift logic, `grader_input_limit` / `grader_model` per-case overrides
- Delete `--no-baseline` CLI flag (meaningless — baselines only run in `make eval`)

## Runtime estimates

**`make test`** (fast tier, Haiku runner, no baselines, no rubric):
- ~23 runs × ~15s each ÷ 8 concurrency ≈ **~45s**
- Deterministic grading adds <1s per case (no LLM calls)
- Target **<90s** comfortably met

**`make eval`** (deep tier, Sonnet runner, lift baselines, rubric grading):
- ~28 runs × ~30s each ÷ 8 concurrency ≈ **~105s** runners
- 28 rubric grader calls (Haiku) × ~3s each ÷ 8 concurrency ≈ **~11s** grading
- Total **~2 minutes**

Both numbers are dominated by Agent SDK startup per case, not by grader cost. If we want to go further, the next bottleneck is the runner itself.

## What gets deleted

**Harness code:**
- `shared_assertions` parsing in `discovery.py`
- `use_shared_assertions` case field handling
- `grader_input_limit` per-case override
- `grader_model` per-case override
- Three-way WARN/OK/FAIL lift logic in `reporter.py`
- `--no-baseline` CLI flag
- Free-form LLM grading as the default path (still used by the rubric grader, but structured)

**Eval files:**
- ~70% of current `{"text": "..."}` assertions — see Appendix A for the full audit
- All `shared_assertions` blocks
- Form-rule assertions like `"Output contains a 'Technique:' line"`

**Tree:**
- `tests/skills/` and `tests/core/` subdirectories
- `tests/skills/<name>/__init__.py` files
- `tests/skills/<name>/test_lint.py` (moved to skill dir)

**Kept unchanged:**
- Agent SDK runner (`runner.py`)
- `tool_called` / `tool_not_called` / `skill_invoked` assertions
- Multi-turn support
- Artifact persistence under `tmp/evals/<timestamp>/`
- Cleanup safety (globs must be under `tmp/` or `references/specs/`)
- Concurrency cap (8), per-case timeout (300s)
- `lint.py` files in skills (renamed assertion key, same scripts)

## Post-MVP (reserved)

- **Model matrix** — `make eval --models=haiku,sonnet,opus` producing a grid per case. Add a model dimension to `RunPlan` and loop in `orchestrator.run_evals`.
- **Saturated-as-error** — promote the WARN to FAIL once the detection logic is proven.
- **Rubric authoring helper** — a small skill or command that suggests initial RUBRIC.md items from SKILL.md.
- **`script_name` extensibility** — dict form for custom script paths: `{"script_name": {"skill": "ghostwrite", "file": "other.py"}}`.
- **Caching** — skip runs whose skill + case haven't changed since the last green run.

## Appendix A — Assertion Migration Audit

For each existing assertion across the four skill suites and two core suites, the table below shows the disposition under Plan B. This is the review list — **nothing gets acted on in Step 4 until these rows are approved**.

**Dispositions:**
- **Convert** — express as one or more deterministic assertions
- **Rubric (C)** — move to `skills/<name>/RUBRIC.md` under `## Critical`
- **Rubric (O)** — move under `## Optional`
- **Rename** — mechanical rename (`lint` → `script_name`)
- **Keep** — already deterministic, no change
- **DELETE** — drop entirely (form rule, redundant, or bloat-inducing)

### ghostwrite (2 cases)

**sponsor-email**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a greeting in the format 'Hey, Sarah --'" | Convert | `{"regex": "^Hey, Sarah --"}` |
| 2 | "Output leads with the results or the ask in the first sentence..." | Rubric (C) | semantic — first-sentence behavior is hard to regex without brittle anchors |
| 3 | `{"lint": "ghostwrite"}` | Rename | `{"script_name": "ghostwrite"}` |
| 4 | "Output contains a sign-off of '- Swift' or 'Happy Hacking,\nSwift'" | Convert | `{"regex": "(- Swift\|Happy Hacking,\\s*\\nSwift)\\s*$"}` |
| 5 | "Output is significantly shorter than the input..." | Convert | `{"output_len_lte": 600}` (input is ~700 chars) |
| 6 | "Output preserves all key facts: 450 fellows, 30% increase, 92% recommendation rate" | Convert | `{"contains_all": ["450", "30%", "92%"]}` |
| 7 | "Output uses contractions (e.g., we're, don't, that's)..." | Rubric (O) | stylistic; regex would miss cases where contractions legitimately don't apply |

**linkedin-from-scratch**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output does NOT contain a full LinkedIn post draft" | Rubric (C) | semantic — hard to define "full post" deterministically |
| 2 | "Output asks the user to provide source content, notes, bullet points, or details to rewrite" | Rubric (C) | semantic |
| 3 | "Output explains that the skill is a rewriter, not a creator" | Rubric (C) | semantic |
| 4 | "Output does not invent the name of the AI company or fabricate partnership details" | Rubric (C) | semantic; enumerating "AI company names" is a losing game |

### summarize (6 cases, all share `{"lint": "summarize"}` today)

Shared `lint` becomes an explicit `{"script_name": "summarize"}` on each case that currently inherits it (all except `short-input-no-padding`, which already overrides via `use_shared_assertions: false`).

**devto-top-article**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a clickable markdown link to the source dev.to URL somewhere near the title..." | Rubric (C) | "near the title" is fuzzy; script_name already checks title existence |
| 2 | "The shareable snippet block includes the source URL" | Rubric (C) | depends on share block shape — summarize/lint.py already validates the block's existence |
| 3 | `{"tool_called": "scrape_as_markdown"}` | Keep | — |
| 4 | `{"tool_not_called": "WebFetch"}` | Keep | — |
| 5 | `{"tool_not_called": "WebSearch"}` | Keep | — |

**devto-rust-tab-orchestrator**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a clickable markdown link to the source URL (https://dev.to/tasenikol/...) near the title" | Convert | `{"regex": "\\[.*\\]\\(https://dev\\.to/tasenikol/[^)]+\\)"}` |
| 2 | "The shareable snippet block includes the source URL" | Rubric (C) | same reasoning as above |
| 3 | "Key points reference specific content from the article: Rust, Chrome tabs, memory pressure, or tab orchestration (not generic commentary)" | Rubric (C) | semantic grounding — regex for keywords misses the "not generic" half |
| 4-6 | Tool assertions | Keep | — |

**anthropic-claude-character**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a clickable markdown link to the source URL (https://www.anthropic.com/research/claude-character) near the title" | Convert | `{"regex": "\\[.*\\]\\(https://www\\.anthropic\\.com/research/claude-character[^)]*\\)"}` |
| 2 | "The shareable snippet block includes the source URL" | Rubric (C) | semantic |
| 3 | "Key points reference specific content: Claude's character, personality, Anthropic's approach to model personality..." | Rubric (C) | semantic grounding |
| 4-6 | Tool assertions | Keep | — |

**local-pdf**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Title is based on the document/paper title or filename (not a URL and not a generic placeholder like 'Summary' or 'Document')" | Rubric (C) | semantic |
| 2 | "The shareable snippet block contains no URL — this is a local PDF with no source URL to share" | Rubric (C) | hard to regex a block-scoped negative |
| 3 | "Key points are grounded in the PDF content, not invented or generic" | Rubric (C) | semantic grounding |
| 4 | `{"tool_called": "Read"}` | Keep | — |
| 5-7 | Tool not-called assertions | Keep | — |

**paste-raw-text**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Title is based on the pasted content (e.g. mentions pull requests, code review, or a related specific concept)..." | Rubric (C) | semantic |
| 2 | "Key points reflect the pasted text (PR size, review time, trunk-based development...)..." | Rubric (C) | semantic grounding |
| 3 | "The shareable snippet block contains no URL..." | Rubric (C) | semantic (block-scoped negative) |
| 4-7 | Tool not-called assertions | Keep | — |

**short-input-no-padding** (opts out of shared lint today — we'll add `script_name` explicitly)

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a clear title for the note (H1 or other visually distinct title line)" | **DELETE** | redundant — summarize's lint.py already checks title presence via `check_title` |
| 2 | "Output contains a short 1-2 sentence summary near the top naming the Q3 demo day date change as the core fact" | Rubric (C) | semantic |
| 3 | "If a bulleted list of points is present, every bullet is directly supported by the 4-sentence input..." | Rubric (C) | semantic grounding against input |
| 4 | "The summary and key points do NOT pad with generic project-management commentary..." | Rubric (C) | this is the whole point of the case — keep in rubric as critical |
| 5 | `{"lint": "summarize"}` | Rename | `{"script_name": "summarize"}` |
| 6 | `{"tool_not_called": "scrape_as_markdown"}` | Keep | — |
| 7 | `{"tool_not_called": "WebFetch"}` | Keep | — |

### scope (3 cases)

**github-webhook-slack**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output proposes 2-3 distinct approaches with trade-offs" | Rubric (C) | semantic counting ("distinct approaches") |
| 2 | "Output includes a clear recommendation with reasoning for which approach to use" | Rubric (C) | semantic |
| 3 | "A spec file is written (to references/specs/ or the designated output directory) with a descriptive name" | Convert | `{"files_written_include": "references/specs/*.md"}` |
| 4 | "No implementation code, project scaffolding, or package.json is created" | Convert | `{"files_written_exclude": "package.json"}` + `{"files_written_exclude": "*.py"}` + `{"files_written_exclude": "*.js"}` + `{"files_written_exclude": "*.ts"}` |
| 5 | "Output includes a self-review step scanning for placeholders or contradictions" | Rubric (O) | semantic, also optional — nice-to-have |
| 6 | "Output asks the user to review the spec before proceeding" | Rubric (C) | semantic |
| 7 | "Output offers what's-next options (implementation plan, scope another piece, etc.)" | Rubric (O) | semantic, optional |
| 8 | "The written spec file mentions per-repo to channel routing (terms like 'allowlist', 'routing table', 'repo -> channel', or equivalent)" | Convert | `{"file_contains": {"path": "references/specs/*.md", "regex": "(?i)(allowlist\|routing table\|repo.{0,10}channel)"}}` |
| 9 | "The written spec file specifies a durable queue or retry mechanism — Redis, BullMQ, persistent queue, or similar..." | Convert | `{"file_contains": {"path": "references/specs/*.md", "regex": "(?i)(Redis\|BullMQ\|persistent queue\|durable queue)"}}` |
| 10 | "The written spec file lists all three event types: opened, ready_for_review, closed" | Convert | 3× `{"file_contains": {"path": "references/specs/*.md", "text": "<event>"}}` |
| 11 | "The written spec file marks the user-stated non-goals as out of scope: two-way interaction, review assignment, backfill, and config UI" | Convert | `{"file_contains": {"path": "references/specs/*.md", "regex": "(?i)out of scope"}}` + Rubric (C) for "mentions each non-goal" |
| 12 | "The written spec file's deployment target is Fly.io and the runtime is Node.js" | Convert | `{"file_contains": {"path": "references/specs/*.md", "text": "Fly.io"}}` + `{"file_contains": {"path": "references/specs/*.md", "text": "Node.js"}}` |
| 13 | "The written spec file mentions YAML config loaded at startup (no hot reload)" | Convert | `{"file_contains": {"path": "references/specs/*.md", "regex": "(?i)YAML"}}` |

**vague-notifications**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output asks at least one clarifying question before proposing approaches" | Convert | `{"regex": "\\?"}` (min: 1) |
| 2 | "Output does not propose a full design or write a spec without first gathering requirements" | Convert | `{"files_written_exclude": "references/specs/*"}` |
| 3 | "Clarifying questions are presented one at a time, not as a big list" | Convert | `{"regex": "\\?", "max": 2}` |
| 4 | "No implementation code or project scaffolding is created" | Convert | `{"files_written_exclude": "*.py"}` + `{"files_written_exclude": "*.js"}` + `{"files_written_exclude": "package.json"}` |

**skip-design-rate-limiter**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output does NOT agree to skip scoping — it still asks at least one clarifying question on this turn" | Convert + Rubric (C) | `{"regex": "\\?"}` for the question + Rubric (C) for "does not agree to skip" |
| 2 | "Output acknowledges the user's urgency AND names a concrete risk of jumping in blind" | Rubric (C) | semantic AND |
| 3 | "No implementation code, project scaffolding, or source files are created" | Convert | `{"files_written_exclude": "*"}` (one-turn case, scope pushes back, writes nothing) |
| 4 | "Output proceeds with scoping steps (clarifying questions or approach proposals)" | Rubric (C) | semantic behavior check |

### prompt-engineer (3 cases)

**contract-extraction-json**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "The final prompt is presented as a distinct fenced code block" | Convert | `{"regex": "```[\\s\\S]*?```"}` (multiline) |
| 2 | "Output contains a 'Technique:' line briefly naming the pattern used" | **DELETE** | **form rule causing bloat** — the skill grew a "Technique:" line only to pass this. If technique is important, ask it in the rubric semantically. |
| 3 | "Output does NOT begin with preamble like 'Here is your prompt' or 'Sure, I can help with that'" | Convert | `{"not_regex": "^(Here is your prompt\|Sure, I can help)"}` |
| 4 | "The prompt inside the code block names all three required fields — parties, effective_date, termination" | Convert | `{"contains_all": ["parties", "effective_date", "termination"]}` |
| 5 | "The prompt explicitly instructs the LLM to return only JSON with no prose wrapper, markdown fences, or commentary" | Rubric (C) | semantic |
| 6 | "The prompt specifies behavior when a required field is missing from the contract (null vs omit vs explicit error)" | Rubric (C) | semantic — testing that the prompt handles a failure mode |
| 7 | "The prompt addresses handling of long or multi-page input (chunking, truncation, or an explicit instruction to process the full document)" | Rubric (C) | semantic |
| 8 | "The prompt does NOT use vague role assignments like 'You are a helpful assistant'" | Convert | `{"not_regex": "(?i)You are (a\|an) (helpful\|friendly)\\s*(AI\\s*)?assistant"}` |

**fix-bad-prompt**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output contains a fenced code block wrapping a rewritten version of the prompt" | Convert | `{"regex": "```[\\s\\S]*?```"}` |
| 2 | "Output contains a 'Changes:' section (or equivalent) with bullets explaining what was fixed and why" | Rubric (C) | "or equivalent" is semantic — don't pin to a literal label |
| 3 | "The diagnosis identifies at least two of: vague role, contradictory instructions, politeness padding, missing output format" | Rubric (C) | semantic counting |
| 4 | "The rewritten prompt removes 'helpful AI assistant', 'please', and 'thank you' padding" | Rubric (C) | block-scoped negative (hard to regex the "rewritten" section cleanly) |
| 5 | "The rewritten prompt specifies a concrete output format" | Rubric (C) | semantic |
| 6 | "The rewritten prompt resolves the 'thorough but concise' contradiction" | Rubric (C) | semantic |
| 7 | "The rewritten prompt is shorter than the original" | Rubric (O) | no clean way to measure the rewritten subset; optional |

**vague-summarization-request**

| # | Assertion | Disposition | Replacement |
|---|---|---|---|
| 1 | "Output asks at least one clarifying question before drafting a final prompt" | Convert | `{"regex": "\\?", "min": 1}` |
| 2 | "Output asks no more than 3 clarifying questions" | Convert | `{"regex": "\\?", "max": 3}` |
| 3 | "Output contains at most two question marks total (one-at-a-time behavior, not a bulk list)" | Convert | `{"regex": "\\?", "max": 2}` (supersedes row 2 — tighter bound) |
| 4 | "Output does NOT deliver a finished prompt in a code block on this turn" | Convert | `{"not_regex": "```[\\s\\S]*?```"}` |
| 5 | "Output does not fabricate specifics the user did not provide (e.g. inventing 'news articles' or 'academic papers' as the content type)" | Rubric (C) | semantic — grader needs to know what the user actually provided |

### Core suites

**skill-triggers** (6 cases, already deterministic-heavy)

| Case | Assertions | Disposition |
|---|---|---|
| ghostwrite-on-rewrite-request | 1 skill_invoked + 1 text | skill_invoked Keep; text → Rubric (C) on "is a rewrite, not a refusal" |
| scope-on-design-request | 1 skill_invoked + 1 text | skill_invoked Keep; text → Rubric (C) on "engages with scoping" |
| summarize-on-tldr-request | 1 skill_invoked | Keep |
| prompt-engineer-on-prompt-request | 1 skill_invoked + 1 text | skill_invoked Keep; text → Rubric (C) on "produces or asks for a prompt" |
| no-skill-on-trivia | 1 tool_not_called + 1 text | tool_not_called Keep; text → Convert `{"contains": "4"}` |
| no-ghostwrite-on-fresh-draft | 2 text | One → `{"skill_not_invoked": "ghostwrite"}` (Convert, uses the new primitive); the second behavioral assertion → Rubric (C) |

**Note on skill-triggers:** `skill-triggers` is a core suite, so it doesn't auto-load a RUBRIC.md. The `skill_not_invoked` primitive added to the vocabulary (see Trace section above) solves the one negative case cleanly. Any remaining behavioral nuance in `skill-triggers` moves to rubric items only if unavoidable; preferred disposition is deterministic.

**no-ai-attribution** (3 cases)

| Case | Assertion count | Notes |
|---|---|---|
| throwaway-commit | 6 text | All convertible to regex / contains / file_contains against the created `fake-repo/` |
| pr-draft | 6 text | Same — regex checks for Co-Authored-By, "Generated with", etc. |
| amend-existing-attribution | 5 text | Same |

These are genuinely structural checks (no semantic grading needed) — all 17 text assertions convert cleanly to `not_regex` / `file_contains` / `contains`. Target: zero rubric items for the `no-ai-attribution` core suite.

### Delete summary

Only **two** assertions are proposed for outright deletion:

1. **prompt-engineer > contract-extraction-json > "Output contains a 'Technique:' line briefly naming the pattern used"** — form rule causing bloat. The skill grew a `Technique:` line only to pass this assertion.
2. **summarize > short-input-no-padding > "Output contains a clear title for the note (H1 or other visually distinct title line)"** — redundant with `script_name: summarize` (lint.py already validates title presence).

Everything else either converts to deterministic or moves to a rubric.

### Primitive discovered during audit

Going through the assertion list in Appendix A surfaced one missing deterministic assertion: `{"skill_not_invoked": "<skill>"}`, the negative mirror of `skill_invoked`. It's already folded into the Trace section of the vocabulary above. Needed cases:

- `no-ghostwrite-on-fresh-draft` (core/skill-triggers) — "the skill should NOT fire here"
- Any future regression guard against over-eager skill activation

## Open questions for user review

Before Step 4 (migration), these need your sign-off:

1. **Delete list** — only 2 assertions proposed for outright deletion (see "Delete summary" above). OK?
2. **`skill_not_invoked`** — adding this primitive so `no-ghostwrite-on-fresh-draft` stays deterministic. OK?
3. **Core suite rubrics** — `no-ai-attribution` gets no rubric (purely structural); `skill-triggers` also gets no rubric (the trigger check + one behavioral assertion per case, most of which convert). OK?
4. **Regex count shorthand** — I folded count semantics into `regex` itself via `min` and `max` fields. Alternative is a separate `regex_count_lte` primitive. The inline version is more uniform. OK?
5. **`files_written_exclude: "*"`** as a valid way to assert "no files were written at all." OK?
