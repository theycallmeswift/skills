# Option C: Two-Tier Eval Suite Implementation Plan

**Goal:** Split the eval suite into a Lift tier (must show delta vs baseline) and a Regression tier (with-skill only, ~100% target), based on Haiku baseline data from 2026-04-08.

**Why:** 10 of 17 cases tied on Opus — looked like suite measured nothing. Haiku run separated real skill value from capability freebies. Matches Anthropic "Demystifying evals" + Agent Skills guide best practices.

**Tech:** Python harness at `tests/support/harness/`, eval JSON at `tests/skills/*/evals.json` and `tests/core/*/eval.json`.

---

## Tiering Decisions (from Haiku data)

**Lift tier (runs both variants, must show positive delta):**
- `ghostwrite/sponsor-email` — Haiku +71%
- `ghostwrite/linkedin-from-scratch` — Haiku 0 delta but Opus +100%; keep as lift for refusal behavior
- `prompt-engineer/fix-bad-prompt` — Haiku +100%
- `scope/vague-notifications` — Haiku +25%
- `scope/skip-design-rate-limiter` — Opus +25%, Haiku 0 delta; keep in lift, tighten assertions

**Regression tier (with-skill only, ~100% target):**
- `ghostwrite/preserve-link-and-quote`
- `prompt-engineer/contract-extraction-json`
- `prompt-engineer/vague-summarization-request`
- `scope/asks-one-question-at-a-time`
- `scope/github-webhook-slack`
- `summarize/ambiguous-reference`
- All `core/*` evals (always regression)

**Rewrite assertions (summarize) — cases depend on rewrite:**
- `summarize/anthropic-claude-character`
- `summarize/devto-top-article`
- `summarize/devto-rust-tab-orchestrator`
- `summarize/local-pdf`
- `summarize/paste-raw-text`
- `summarize/short-input-no-padding`

Convert rigid literal-heading assertions (`## TL;DR`, `## Share`, `## Comment`) to semantic checks (has a short summary section, has a bulleted key-points list, has a shareable fenced snippet with source URL). After rewrite, classify each case into lift or regression based on whether the skill actually changes behavior.

---

## Implementation

### Task 1: Add `tier` field to eval schema

**Files:**
- Modify: `tests/support/harness/eval.schema.json`
- Modify: `tests/support/harness/models.py`
- Modify: `tests/support/harness/discovery.py`
- Modify: `tests/support/harness/test_discovery.py`

- [ ] Add `tier` enum (`"lift"` or `"regression"`) to the per-case schema. Default `"regression"` if omitted (safer default — only opt into the stricter lift bar).
- [ ] Add `tier: Literal["lift", "regression"] = "regression"` to `EvalCase` dataclass in `models.py`.
- [ ] Parse `tier` in `discovery.py`'s case loader.
- [ ] In `build_run_plans`, only emit the baseline variant when `tier == "lift"`. Regression cases emit only the `with_skill` run plan.
- [ ] Update `test_discovery.py`: add a test that a `tier: lift` case produces 2 run plans and a `tier: regression` case produces 1.
- [ ] Run `make test-unit`. Expect all green.
- [ ] Commit: `feat(harness): add tier field to eval schema for lift vs regression split`

### Task 2: Reporter surfaces tiered results

**Files:**
- Modify: `tests/support/harness/reporter.py`
- Modify: `tests/support/harness/test_reporter.py`

- [ ] Split the `## Skill Eval Results` table into two sections: `## Lift Suite` (shows With Skill / Baseline / Delta) and `## Regression Suite` (shows Result only, single column).
- [ ] Lift tier fail condition: with-skill below 100% OR delta ≤ 0 (configurable default: delta must be positive).
- [ ] Regression tier fail condition: with-skill below 100%.
- [ ] Update existing reporter tests; add a test case per tier for pass and fail.
- [ ] Commit: `feat(harness): split reporter output into lift and regression sections`

### Task 3: Tag existing eval files with tiers

**Files:**
- Modify: `tests/skills/ghostwrite/evals.json`
- Modify: `tests/skills/prompt-engineer/evals.json`
- Modify: `tests/skills/scope/evals.json`
- Modify: `tests/skills/summarize/evals.json` (ambiguous-reference only for now; others rewritten in Task 4)

- [ ] For each case listed in the Lift tier section above, add `"tier": "lift"`.
- [ ] All others default to `"regression"` (or explicitly mark, reviewer preference — prefer explicit).
- [ ] Do NOT touch summarize cases flagged for rewrite yet.
- [ ] Run `make test-unit`. Expect green.
- [ ] Commit: `chore(evals): tag existing cases with lift/regression tiers`

### Task 4: Rewrite summarize assertions semantically

**Files:**
- Modify: `tests/skills/summarize/evals.json`

- [ ] For shared and case-specific assertions, replace literal heading checks (`Output contains a '## TL;DR' section`) with semantic checks graded by LLM:
  - "Output begins with a short 1-2 sentence summary of the content" (replaces TL;DR literal check)
  - "Output contains a bulleted list of 5-8 key points from the source" (replaces Cliff Notes literal check)
  - "Output contains a fenced code block with a shareable one-sentence hot take and the source URL on its own line" (replaces Share section literal check; drop for non-URL inputs)
  - "Output contains a fenced code block with a short (≤20 word) forum comment" (replaces Comment literal check)
- [ ] Keep H1-title deterministic structural check ONLY where the skill template is strictly required (`devto-*`, `anthropic-claude-character`); drop for pasted text and short inputs where prose format is also valid.
- [ ] Re-run that specific suite: `make test ARGS="summarize"`. Inspect failures; iterate on assertion wording.
- [ ] Classify each case into lift or regression based on whether the skill changes behavior in practice.
- [ ] Commit: `fix(evals): replace brittle literal-heading checks with semantic assertions`

### Task 5: Delete confirmed capability freebies

**Files:**
- Modify: eval JSONs identified as having no behavioral signal on either Opus or Haiku, or move them to a `references/archived/` note.

- [ ] Candidates: any case where both Opus AND Haiku showed 100/100 with no delta and the assertion is generic. Review list with Swift before deleting. For now, keep everything tiered and let the next full run drive deletions.
- [ ] Skip if no consensus in review.
- [ ] Commit (if any deletions): `chore(evals): drop saturated capability freebies`

### Task 6: Full validation run

- [ ] Run `make test` on Opus (default) — expect Lift and Regression sections in output, all regression cases green, lift cases showing positive delta.
- [ ] Run `make test ARGS="--model claude-haiku-4-5-20251001"` — expect meaningful data in both sections; most lift deltas should be larger on Haiku than Opus.
- [ ] Save both results to `tmp/evals/` and compare deltas between model runs.
- [ ] Update `docs/evals.md` with the two-tier model and when to add a case to each tier.
- [ ] Commit: `docs(evals): document lift vs regression tier model`

### Task 7 (out of scope, follow-up): no-ai-attribution hook

Haiku put "Generated with Claude Code" in a PR body 4/6 runs. Instructions alone aren't enough. Separate PR: add a PreToolUse hook blocking commits/PRs containing forbidden attribution strings, keep the eval as regression coverage on the hook's effect. Track separately.

---

## Verification

After Task 6:
- Running `make test` (Opus) produces clearly labeled Lift and Regression sections.
- Lift cases each show a positive delta; regression cases are at 100%.
- Running `--model claude-haiku-4-5-20251001` produces the same shape and is the primary signal for "does the skill still earn its keep."
- `make test-unit` still green (≥51 passing).
- `docs/evals.md` explains the two-tier model.
