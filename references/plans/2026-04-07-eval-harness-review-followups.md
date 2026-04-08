# Eval Harness Review Followups

**Date:** 2026-04-07
**Branch reviewed:** `eval-harness-overhaul` (vs `dev`)
**Status:** Draft plan, not yet executed

This plan captures findings from a code review of the eval harness overhaul. It is organized so another agent can pick up each item independently. Findings are bucketed by priority. Nothing in this plan has been implemented yet.

## Scope of the review

- All `tests/skills/*/evals.json` and `tests/core/*.json`
- `tests/support/harness/` (discovery, runner, grader, orchestrator, reporter, models, `__main__`)
- `tests/support/harness/test_*.py`
- `docs/evals.md`

Priorities (from request):
1. Are evals testing the *spirit* of each skill, or just surface formatting?
2. Python code quality / formatting in the harness
3. Major gaps in coverage

---

## Critical (must fix)

### C1. Ghostwrite suite is missing the adversarial / negative case promised by the docs

`docs/evals.md` says "At least 3 cases per skill: happy path, edge case, adversarial/negative." Ghostwrite (`tests/skills/ghostwrite/evals.json`) only has 2: `sponsor-email` and `linkedin-from-scratch`. The "rewriter-only" guard in `linkedin-from-scratch` is good, but there is no edge case for the actual rewriting behavior (e.g. content that already contains em dashes that need stripping, content with quotes or links to preserve, very short input that should be lightly touched, or input the user wants kept formal).

Action:
- Add a third case `preserve-link-and-quote` (or similar) with input containing a URL, a direct quote attributed to a third party, and at least one em dash. Assertions should verify:
  - Em dash removed / replaced
  - URL preserved verbatim
  - Quoted text preserved verbatim (no paraphrasing inside quotes)
  - Output still in Swift's voice (lowercase greeting, contractions, no preamble)
- Optional fourth: a short Slack one-liner where the rewrite should *not* expand the content into paragraphs (guards against the model over-writing).

### C2. Prompt-engineer `contract-extraction-json` over-indexes on output framing, not prompt quality

The case currently asserts things like "presented as a distinct fenced code block", "Technique: line after the code block", "does NOT begin with preamble". Those are real conventions from the skill, but together they are 4 of 6 assertions on output *shell* and only 2 on the *prompt itself* ("specifies a concrete JSON schema", "self-contained"). A model can pass this case while producing a mediocre prompt.

Action:
- Keep the framing checks but rebalance: add assertions that test the produced prompt's quality, e.g.:
  - The prompt explicitly instructs the LLM to return *only* JSON (no prose wrapper)
  - The prompt names all three required fields (`parties`, `effective_date`, `termination`) inside the schema, not just in the surrounding text
  - The prompt specifies behavior when a field is missing from the contract (null vs omit vs error) — this is the real failure mode of extraction prompts
  - The prompt mentions handling multi-page / long input (chunking, truncation, or "process the full document")
- Drop or merge one of the redundant framing assertions so total count stays manageable.

### C3. Scope `github-webhook-slack` happy-path assertions don't verify the spec's *content*

The case scripts a full multi-turn dialogue and asserts that a spec file is written, that there's a self-review step, that no code is created, etc. None of the assertions check whether the spec actually reflects the user's stated requirements (per-repo allowlist, retries / crash safety, YAML config at startup, Fly.io + Redis, opened/ready_for_review/closed events, internal eng team of ~15). A scope skill that writes a generic webhook spec ignoring half the user's constraints would still pass.

Action:
- Add assertions that read the written spec (the grader receives `files_written`, so it can quote it):
  - Spec mentions per-repo → channel routing (or "allowlist" / "routing table")
  - Spec mentions a durable queue / retry mechanism (Redis, BullMQ, etc.) — not in-memory
  - Spec lists the three event types the user named (`opened`, `ready_for_review`, `closed`)
  - Spec marks the user-stated non-goals as out of scope (two-way interaction, review assignment, backfill, config UI)
  - Spec deployment target is Fly.io / Node.js (matches stated stack)
- Keep existing process-quality assertions but make at least 4 of the assertions content-based.

### C4. Summarize suite has zero adversarial / negative coverage

All four summarize cases are happy paths with the same ~12 structural assertions repeated almost verbatim. There is no:
- Case where brightdata fails / page is unreachable (does the skill fail loudly, or silently fall back to WebFetch?)
- Case where the user pastes raw text instead of a URL (should summarize without scraping)
- Case where the input is *already* a summary or extremely short (should not pad)
- Case asserting the skill refuses or asks when given an ambiguous reference ("summarize that thing I sent you yesterday")

Also: the four cases each repeat ~12 assertion strings verbatim. If the format definition shifts, all four must be edited in lockstep. This is a maintainability smell, but not a correctness bug — see I3.

Action:
- Add `paste-raw-text` case: paste 800 words of an article body, assert no scrape tool is called and the standard summarize output structure is produced.
- Add `short-input-no-padding` case: paste a 4-sentence note, assert the output doesn't invent Cliff Notes bullets that aren't grounded in the source (grader checks each bullet against the input).
- Add `ambiguous-reference` case: ask "summarize that thing" with no link, assert the skill asks for clarification rather than scraping something arbitrary.

### C5. `no-ai-attribution` core eval may be testing a tautology in `pr-draft`

The `pr-draft` case asks the agent to "write out (as plain text in your reply) the title and body you would use for a pull request" — it never executes `gh pr create`. Then asserts "No `gh pr create` was actually executed". The assertion will trivially pass because the prompt forbade the action.

Action:
- Either remove the "no gh executed" assertion (it's tested by the prompt itself, not by the rule we care about), or replace the case with one where the agent is given freedom to act and we verify it doesn't add attribution under realistic pressure. A better adversarial framing: tell the agent "make a commit and write a PR description, follow your normal conventions" and grade *only* the attribution rule. The current phrasing "Do not run gh, do not push" makes the test artificial.
- Add a third case where the agent is asked to amend / rewrite a commit that *already* contains a `Co-Authored-By` trailer in its message (seeded via `files`), and assert the rewrite strips the trailer rather than preserving it. This tests the rule under the harder condition of "remove existing attribution," which is where models commonly fail.

---

## Important (should fix)

### I1. `skill-triggers` core eval doesn't actually verify the Skill tool name

Assertions read "The Skill tool was invoked with a skill name matching 'ghostwrite' (check the TOOL TRACE)". The grader receives the tool trace as JSON and is asked to interpret. But the trace records the *raw tool name and input*. For the Claude Code plugin, the tool used is `Skill` and the skill name is in `input.skill`. The assertion text is loose enough that the grader may PASS on any `Skill` invocation regardless of the actual skill name, or FAIL if the name appears only in the input dict.

Action:
- Make assertions explicit about where to look: `"The TOOL TRACE contains an entry where name == 'Skill' and input.skill == 'mechaswift:ghostwrite' (or 'ghostwrite')"`.
- Consider adding a deterministic helper instead of the LLM judge for this specific check — see I5.

### I2. Multi-turn scripts are static and brittle (acknowledged in docs, but not mitigated)

`docs/evals.md` calls this out: "If the agent asks something the script didn't anticipate, the reply may be a non-sequitur." The `scope/github-webhook-slack` case is the prime example — turn 2 dumps every answer in one paragraph regardless of what was asked. This makes the test fragile and means we're not really testing the "one question at a time" property the skill enforces.

Action (pick one):
- (a) Add a `pre_answers` field on cases: a dict the harness can use to feed the model a "scripted user" reply that depends on the last assistant turn's content. Implement by having a tiny LLM call between turns that picks the closest pre-canned answer.
- (b) Cheaper: split `github-webhook-slack` into two cases — a "process" case (very short, asserts the skill asks one question at a time and waits) and a "content" case (uses a single mega-turn that pre-answers everything and grades the produced spec). The current case tries to do both and does neither well.
- Recommendation: (b) for now; revisit (a) if multi-turn coverage grows.

### I3. Summarize assertion duplication

Each of the four summarize cases copy-pastes the same ~10 structural assertions (H1, TL;DR, Cliff Notes 5-8 bullets, Share fence, Comment fence, etc.). When the format changes, all four must be updated in lockstep and they will drift.

Action:
- Add a JSON-level mechanism for shared assertion sets. Two options:
  - Extend `discovery.load_eval_file` to honor a top-level `shared_assertions` array on the suite that gets merged into every case's assertions.
  - Or: support `"include_assertions": "format"` referencing a named group defined once in the file.
- Migrate summarize to use it. Keep per-case assertions only for the things that differ (e.g. `local-pdf` uses Read, others use brightdata).

### I4. Grader prompt has no protection against very long `stdout` / `files_written`

`grader.py` `_build_prompt` interpolates the entire stdout, full file contents, and full tool trace into one prompt string. A long scope multi-turn run easily blows past 50k tokens, and the harness raises buffer to 64MB. Haiku will accept it, but cost and latency balloon, and graders get confused by giant payloads.

Action:
- Truncate `stdout` to the last N chars (e.g. 40k) with a `[... truncated M chars ...]` marker, prefer the *tail* since that's where the final answer lives. Same for individual files.
- Truncate `tool_trace` to the last 50 entries.
- Make limits configurable on the case (`grader_input_limit`) for cases that legitimately need more.
- Consider passing `stdout` chunks per turn instead of a single blob for multi-turn.

### I5. Tool-trace assertions should not go through the LLM judge

For deterministic facts ("brightdata was called", "WebFetch was not called", "Skill tool fired with name X"), an LLM judge is overkill, slower, and occasionally wrong. The harness already has structured `tool_trace` data.

Action:
- Add a second assertion type alongside `text`: `{"tool_called": "mcp__brightdata__scrape_as_markdown"}`, `{"tool_not_called": "WebFetch"}`, `{"skill_invoked": "ghostwrite"}`. These are evaluated in Python in `grader.py` before (or instead of) the LLM call and merged into the `Grading` result.
- Migrate the existing TOOL TRACE assertions in summarize and skill-triggers to the new types.
- Keep text assertions as the default for everything else.

### I6. `_run_one` cleanup runs against `project_root`, not the temp cwd

```python
for pattern in plan.case.cleanup:
    for match in project_root.glob(pattern):
```

The cleanup glob is matched against `project_root`, not the temp cwd. That's actually intentional for cases like `scope/github-webhook-slack` whose spec gets written to `references/specs/` *inside the real repo* (because the SDK is run with `cwd=tmp` but plugins are loaded from project_root and the skill writes via absolute paths into the user's repo? — needs verification). Either way, this is dangerous: a buggy or malicious cleanup glob can delete real repo files.

Action:
- Verify whether scope writes specs inside the temp cwd or inside the real `project_root/references/specs/`. If it's writing into the real repo, that is a *much* bigger bug — the harness is supposed to isolate runs.
- Once the right location is known: scope cleanup globs to *only* `project_root/references/specs/`, `project_root/tmp/`, and other known-safe roots. Reject globs containing `..` or absolute paths.
- Add a unit test that asserts a cleanup pattern like `*` or `../*` is rejected.

### I7. The temp cwd is removed *before* cleanup runs and *before* artifacts are persisted

In `_run_one`:

```python
with tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
    cwd = Path(tmp)
    run = await run_claude(...)
# tmp is gone here
for pattern in plan.case.cleanup: ...
adir = _artifact_dir(...)
(adir / "outputs" / "output.md").write_text(run.stdout)
```

`run.files_written` was captured inside the `with` block, so its contents are in memory — fine. But if a future change tries to copy files from the cwd into artifacts (a likely next step for debugging failed runs), it will silently get nothing. Worth restructuring now.

Action:
- Move the `tempfile.TemporaryDirectory` so its scope ends *after* artifact persistence, or persist the relevant files into `adir` before the `with` block exits.
- Add `files_written` to the artifact metadata (we already have it; just dump it as JSON next to `output.md`).

---

## Suggestions (nice to have)

### S1. Python code quality nits in the harness

- `runner.py`: `from claude_agent_sdk import ...` happens inside `run_claude`. This is fine for lazy import but means the module isn't checked at import time. Move to module level unless there's a known startup-cost reason.
- `runner.py`: `async def run_codex` and `run_gemini` raise `NotImplementedError` and accept `*args, **kwargs`. Either delete (YAGNI) or add a `# pragma: no cover` and a real signature so callers don't lose type help.
- `orchestrator.py` line 45: `import shutil; shutil.rmtree(...)` — move the import to module level.
- `orchestrator.py`: `_run_one` is doing too much (run, cleanup, grade, write artifacts, return result). Split into `_execute`, `_persist_artifacts`, `_cleanup` for testability.
- `grader.py`: the manual fence-stripping fallback (`raw.startswith("```")` etc.) is dead code if `structured_output` always works on the current SDK. If you want to keep it as a safety net, extract it to a `_parse_grader_response` helper and add a unit test.
- `discovery.py`: `_load_turns` raises `ValueError` with a helpful message — good. Do the same for missing `name` or `evals` keys (currently a raw `KeyError` from `data["name"]` / `data["evals"]`).
- `models.py`: `EvalCase.assertions: list[dict]` should be `list[dict[str, Any]]` or a typed dataclass. As written it's untyped and the rest of the codebase indexes into it stringly.
- `reporter.py`: `RichReporter._table` rebuilds the entire table on every update (fine for small N but quadratic). `_rows` is keyed by tuple but iteration order is insertion order — explicit comment would help.
- `__main__.py`: `Path(__file__).resolve().parents[3]` is fragile to file moves. Add an assertion `assert (project_root / "AGENTS.md").exists()` so failure is loud.
- No `ruff`/`black`/`mypy` config for the harness. Add a `[tool.ruff]` block to `pyproject.toml` and run it in CI / `make test`.
- Several files mix `from .x import Y` and bare `from typing import` ordering. Run `ruff --select I` to fix import order.

### S2. Harness has no test for the orchestrator end-to-end

`tests/support/harness/` has unit tests for `discovery`, `grader`, `runner`, `reporter` — but nothing for `orchestrator.run_evals`. Even a fake-runner-fake-grader test that verifies "given two suites, builds N plans, writes N artifact dirs" would catch the I7 ordering bug above.

Action:
- Add `test_orchestrator.py` that monkey-patches `runner.run_claude` and `grader.grade` with stubs and runs `run_evals` against a temp project tree.

### S3. Reporter unit test asserts very little

`test_reporter.py` likely just instantiates and checks no-throw. Worth verifying the exit code logic explicitly: failing assertion → 1, run error → 1, baseline-only failure → 0, all pass → 0. (Confirm by reading and expand if missing.)

### S4. `skill-triggers` only tests positive triggering, never negative

Every case is "user phrases X, skill Y should fire". There is no "user phrases unrelated to any skill, no skill should fire" case. Without it, the test passes a model that fires *every* skill on *every* prompt.

Action:
- Add `no-skill-on-trivia` case: prompt is "what's 2+2?" — assert the Skill tool was *not* invoked at all.
- Add `no-ghostwrite-on-fresh-draft`: prompt is "write me a brand new blog post about Rust" — assert ghostwrite did not fire (it's a rewriter, not a drafter — this matches the user memory `feedback_ghostwrite_rewriter_only`).

### S5. `prompt-engineer/vague-summarization-request` assertion #3 is awkward to grade

`"Questions are presented one at a time, not as a numbered list of 5+ questions"` — the LLM judge has to count and infer intent. Sharper restatement: `"Output contains exactly one question mark, or fewer than three questions total"`.

### S6. Eval JSON schema is unenforced

Hand-written JSON has caught typos in the past (turns vs turn, asserting vs assertions). Add a JSON Schema (`tests/support/harness/eval.schema.json`) and validate at discovery time with a clear error.

### S7. Docs gap: `docs/evals.md` doesn't mention deterministic tool-trace assertions, cleanup safety, or the static-multi-turn caveat

After implementing I5, I6, I2 above, update `docs/evals.md` accordingly. Also document the assertion-style guide:
- Prefer testable observable properties
- Avoid surface-only assertions (length, char counts, backtick counts) unless they're load-bearing
- Anchor at least half the assertions in *content* not *form*

### S8. Consider grouping `tests/support/` so harness tests don't run as part of the eval suite by accident

`make test` invokes the harness CLI. `uv run pytest tests/support` runs the unit tests. These are different surfaces. Add a `make test-unit` target so contributors don't have to remember the second command.

---

## Suggested execution order

1. C6 / I6 / I7 first — these are correctness/safety bugs in the harness itself. Fix before relying on results.
2. I5 (deterministic tool-trace assertions) — unlocks tightening C5 and I1 cleanly.
3. I3 (shared assertion sets) — small refactor that makes C4 additions cheap.
4. C1–C5 content additions in any order.
5. I2 split of github-webhook-slack.
6. I4 grader truncation.
7. S1 code-quality sweep + ruff/mypy config.
8. S2 / S3 / S4 test additions.
9. S6 / S7 / S8 docs and schema polish.

## Out of scope for this plan

- Changing the LLM grader model.
- Adding Codex / Gemini runners (the stubs in `runner.py` are fine to leave alone or delete per S1).
- Restructuring `tests/` layout.
- Anything in `references/plans/2026-04-07-eval-harness-overhaul.md` itself — that doc is the *source* plan for the branch under review and was not re-litigated here.
