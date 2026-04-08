# Eval Content Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the biggest content holes in three skill eval suites — ghostwrite (missing an edge case), prompt-engineer (over-indexes on output framing), and scope (happy-path asserts process, not spec content).

**Architecture:** Pure eval-JSON edits. No harness changes. Each task adds or rebalances assertions to test observable properties of the output and file contents, not just formatting shell.

**Tech Stack:** JSON, LLM judge.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items C1, C2, C3.

**Depends on:** Nothing strictly, but cleaner if plan 02 (deterministic assertions) has landed so scope content checks don't compete with tool-trace LLM grading.

---

## Context the implementer needs

- Ghostwrite has 2 cases today: `sponsor-email` and `linkedin-from-scratch`. Both are happy-path and negative-case. No edge case for the rewriting behavior itself.
- Prompt-engineer's `contract-extraction-json` has 6 assertions, 4 of which test output-shell conventions (code fence, "Technique:" line, no preamble) and only 2 of which test the *quality of the produced prompt*. A mediocre prompt can pass.
- Scope's `github-webhook-slack` has 7 assertions, all about *process* (proposed approaches, wrote spec, self-review step). None check whether the written spec actually reflects the user's constraints: per-repo allowlist, Fly.io + Redis, Node.js, `opened`/`ready_for_review`/`closed`, ~15 engineers, durable retry, YAML config at startup, non-goals.
- The grader has access to `files_written` — it can read the spec file content and grade against it. This is the core technique for C3.
- For ghostwrite's new case, the grader sees `stdout`. Quoted text preservation is verifiable ("Does the output contain this exact quoted string?").

---

## Task 1: Ghostwrite — add `preserve-link-and-quote` edge case

**Files:**
- Modify: `tests/skills/ghostwrite/evals.json`

The case gives the skill content containing a URL, a direct quote from a third party, and an em dash. The rewrite must strip the em dash, preserve the URL verbatim, preserve the quoted text verbatim, and still sound like Swift.

- [ ] **Step 1: Append the case**

Add to the `evals` array in `tests/skills/ghostwrite/evals.json` (after `linkedin-from-scratch`):

```json
    {
      "id": "preserve-link-and-quote",
      "turns": [
        "Rewrite this as a short blog post intro in my voice:\n\nI was reading through Julia Evans' latest post the other day — she made a point that really stuck with me: \"the best debugging tool you have is the ability to notice when your mental model of the system is wrong.\" The full post is over at https://jvns.ca/blog/2023/11/06/debugging-tools/ and it's genuinely one of the clearest things I've read about how senior engineers actually debug stuff in the wild. I wanted to share it because I think a lot of what we tell junior engineers about debugging misses this point entirely."
      ],
      "files": [],
      "assertions": [
        {"text": "Output does not contain any em dashes (\u2014)"},
        {"text": "Output preserves the URL https://jvns.ca/blog/2023/11/06/debugging-tools/ verbatim (character-for-character)"},
        {"text": "Output preserves the direct quote 'the best debugging tool you have is the ability to notice when your mental model of the system is wrong' verbatim — no paraphrasing inside the quotation marks"},
        {"text": "Output attributes the quote to Julia Evans (the attribution survives the rewrite)"},
        {"text": "Output uses contractions (e.g., it's, we're, that's)"},
        {"text": "Output does not begin with preamble like 'Here is your rewritten post' or 'I rewrote this'"},
        {"text": "Output is a rewrite, not a refusal — actual prose is produced, not a clarifying question"}
      ]
    }
```

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness ghostwrite --no-baseline`
Expected: 3 cases run. Inspect `tmp/evals/<latest>/ghostwrite/eval-preserve-link-and-quote/with_skill/outputs/output.md` and confirm the model preserved the URL and quote. If assertions fail, the model itself is the finding — do not weaken the assertions.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/ghostwrite/evals.json
git commit -m "test(ghostwrite): add preserve-link-and-quote edge case"
```

---

## Task 2: Prompt-engineer — rebalance `contract-extraction-json` toward prompt quality

**Files:**
- Modify: `tests/skills/prompt-engineer/evals.json`

Drop one redundant framing assertion, keep the code-fence + no-preamble checks, and add four content-quality assertions that test what's *inside* the generated prompt.

- [ ] **Step 1: Replace the case's assertions**

In `tests/skills/prompt-engineer/evals.json`, replace the `assertions` array of the `contract-extraction-json` case with:

```json
      "assertions": [
        {"text": "The final prompt is presented as a distinct fenced code block"},
        {"text": "Output contains a 'Technique:' line briefly naming the pattern used"},
        {"text": "Output does NOT begin with preamble like 'Here is your prompt' or 'Sure, I can help with that'"},
        {"text": "The prompt inside the code block names all three required fields — parties, effective_date, termination — inside the schema itself, not just in surrounding prose"},
        {"text": "The prompt explicitly instructs the LLM to return only JSON with no prose wrapper, markdown fences, or commentary"},
        {"text": "The prompt specifies behavior when a required field is missing from the contract (null vs omit vs explicit error) — a real extraction failure mode"},
        {"text": "The prompt addresses handling of long or multi-page input (chunking, truncation, or an explicit instruction to process the full document)"},
        {"text": "The prompt does NOT use vague role assignments like 'You are a helpful assistant'"}
      ]
```

Count: 8 assertions, 3 framing + 5 content. (Dropped: "The prompt inside the code block specifies a concrete JSON schema or output structure" — subsumed by the new "names all three required fields inside the schema" assertion; and "The prompt is self-contained" — too soft to grade reliably, replaced by the two concrete operational checks.)

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness prompt-engineer --no-baseline`
Expected: 3 cases run. The `contract-extraction-json` case now tests prompt quality more rigorously. If the model's prompt doesn't handle missing fields or long inputs, that's a legitimate finding.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/prompt-engineer/evals.json
git commit -m "test(prompt-engineer): rebalance contract-extraction toward prompt quality"
```

---

## Task 3: Scope — add content-based assertions to `github-webhook-slack`

**Files:**
- Modify: `tests/skills/scope/evals.json`

Keep the existing 7 process assertions and add 6 content assertions that read the written spec file. The grader receives `files_written` containing the spec text, so assertions can reference its content directly.

**Note:** Plan 05 splits this case into a "process" variant and a "content" variant. For this plan we're only adding assertions; the split can happen in plan 05.

- [ ] **Step 1: Add content assertions**

In `tests/skills/scope/evals.json`, update the `assertions` array of the `github-webhook-slack` case to append these entries after the existing 7:

```json
        {"text": "The written spec file mentions per-repo to channel routing (terms like 'allowlist', 'routing table', 'repo -> channel', or equivalent)"},
        {"text": "The written spec file specifies a durable queue or retry mechanism — Redis, BullMQ, persistent queue, or similar — NOT an in-memory-only queue"},
        {"text": "The written spec file lists all three event types the user named: opened, ready_for_review, closed"},
        {"text": "The written spec file marks the user-stated non-goals as out of scope: two-way interaction, review assignment, backfill, and config UI"},
        {"text": "The written spec file's deployment target is Fly.io and the runtime is Node.js (matches the user's stated stack)"},
        {"text": "The written spec file mentions YAML config loaded at startup (no hot reload)"}
```

Final assertion count for `github-webhook-slack`: 13 (7 process + 6 content).

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness scope --no-baseline`
Expected: 3 cases run. The `github-webhook-slack` case writes a spec file; grading.json expectations now mix process and content. Check the artifact dir's `files_written.json` (added in plan 01) or the grader's view of files to confirm the spec actually lands somewhere the grader can read it.

**If the spec is being written to the real repo** (possible latent bug — see plan 01 Task 1), land plan 01 first so the `files_written` path is properly captured and `cleanup` is scoped safely.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/scope/evals.json
git commit -m "test(scope): add content assertions for github-webhook-slack spec"
```

---

## Verification

- [ ] `uv run python -m tests.support.harness ghostwrite --no-baseline` — 3 cases, preserve-link-and-quote present
- [ ] `uv run python -m tests.support.harness prompt-engineer --no-baseline` — 3 cases, contract-extraction-json now has 8 assertions with 5 content-quality checks
- [ ] `uv run python -m tests.support.harness scope --no-baseline` — 3 cases, github-webhook-slack now has 13 assertions
- [ ] Spot-check a failing assertion in one of the new cases: is it a legitimate finding (model produced weak output) or a mis-written assertion? If the latter, fix the assertion text; if the former, leave the failure in place and move on.

## Out of scope for this plan

- Splitting `github-webhook-slack` into separate process and content cases (plan 05)
- Grader truncation for long multi-turn runs (plan 05)
- Harness polish (plan 06)
