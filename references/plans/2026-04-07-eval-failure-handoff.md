# Eval Failure Handoff

**Date:** 2026-04-07
**Context:** After the 2026-04-06 skill-improvements PR (#1), the full eval suite passes 92/97 with-skill (94%) and 13/13 project. Three skill evals still have failing assertions on the with-skill run. This document captures what to rerun, what failed, and candidate fixes to consider in a follow-up session.

Source workspace for the last run: `tmp/evals/2026-04-07T04-00-00/`

---

## How to reproduce

Run only the failing evals:

```
/eval ghostwrite prompt-engineer
```

Or target individually:

```
/eval ghostwrite          # eval-2 is the failing case
/eval prompt-engineer     # eval-1 and eval-2 both leak em dashes
```

Each rerun produces a fresh `tmp/evals/<timestamp>/` workspace. If a with_skill `outputs/output.md` is missing after the runners finish, re-dispatch that single runner before grading — two summarize runners silently dropped their output last time.

---

## Failure 1: ghostwrite eval-2 (LinkedIn post from thin air)

**Score:** 1/4 with_skill (same as baseline — skill provides no lift here)

**Eval prompt:** Asks ghostwrite to write a LinkedIn post about an MLH/AI partnership with no source material provided.

**Failed assertions:**
- Output does NOT contain a full LinkedIn post draft
- Output asks the user to provide source content, notes, bullet points, or details to rewrite
- Output explains that the skill is a rewriter, not a creator

**What's happening:** The skill happily drafts a complete post (hook, body, stat, CTA, hashtags) using `[AI Company]` as a placeholder. It never refuses, never asks for source material, never explains its scope.

**Root cause:** `skills/ghostwrite/SKILL.md` has no rewriter-vs-creator gate. Nothing in the workflow says "if no source content is provided, stop and ask." The skill description triggers on rewriting tasks but the body doesn't enforce that boundary.

**Candidate fixes (pick one or combine):**
1. **Add a Step 0 / preflight gate** at the top of `## How to Rewrite`: "If the user has not provided source content (notes, bullets, draft, transcript, article), do not draft anything. Reply: 'Ghostwrite is a rewriter, not a generator. Paste the source content (notes, bullets, rough draft) and I'll rewrite it in Swift's voice.' Stop."
2. **Tighten the skill description** so it doesn't activate on "write me a post about X" — only on rewrite-shaped requests. Probably not enough on its own; the skill still needs the runtime gate.
3. **Add an explicit anti-pattern** to the skill: "Never invent facts, stats, partnerships, quotes, or `[Bracket Placeholders]` for missing content."

Suggested combo: #1 + #3. The gate prevents the failure mode; the anti-pattern catches edge cases where the user provides *some* content but not enough.

**Decision (Mike, 2026-04-07):** Rewriter-only gate is **absolute**. No carve-outs for short fact-bearing prompts. If there's no source content to rewrite, ghostwrite stops and asks. Period.

---

## Failure 2: prompt-engineer eval-1 (em dashes in JSON extractor prompt)

**Score:** 6/7 with_skill (only the no-em-dashes assertion fails)

**Eval prompt:** Asks prompt-engineer to write a system prompt that extracts structured JSON from messy customer support emails.

**Failed assertion:** Output contains no em dashes (—)

**Evidence:** Em dashes on lines 28, 69, 70, 74, 75, 85 — e.g. `Return only the JSON object — no markdown fences`.

## Failure 3: prompt-engineer eval-2 (em dash in rewritten summarizer)

**Score:** 7/8 with_skill (only no-em-dashes fails)

**Eval prompt:** Asks prompt-engineer to fix a broken article-summarization prompt.

**Failed assertion:** Output contains no em dashes (—)

**Evidence:** Line 13: `they add tokens and change nothing`.

### Shared root cause (both failures)

The prompt-engineer skill has no instruction about em dashes. Mike's "no em dashes" rule lives in `references/about-swift.md` (loaded by ghostwrite) and in user memory. The prompt-engineer skill never reads it, and the model defaults to em dashes when writing prose-style instructions inside the generated prompts.

The em dashes appear in the *generated prompt content*, not in prompt-engineer's own commentary. So this is about what the skill produces, not how the skill talks.

### Candidate fixes

1. **Add to the Quality Bar** in `skills/prompt-engineer/SKILL.md`: "**No em dashes.** Use commas, periods, or parens. Em dashes read as AI-generated and Mike's audience filters on this."
2. **Add to the Anti-Patterns list:** "Em dashes (—) anywhere in the output — including inside the generated prompt."
3. **Add a final scan step** to the workflow: "Before delivering, grep your output for `—` and replace each one. This is a hard rule for Mike's content, including prompts you write for him."

Suggested combo: #1 + #3. The Quality Bar item gives the model the rule; the explicit scan step turns it into an action.

**Risk to watch:** Don't import the no-em-dashes rule by reading `references/about-swift.md` — that file is voice-shaped and would pull in tone/voice rules that don't belong in prompt-engineer's output. Inline the single rule instead.

---

## Suggested execution order

1. Fix prompt-engineer em dashes first — small, surgical, two near-identical evals will both flip green.
2. Run `/eval prompt-engineer` to confirm.
3. Then fix ghostwrite eval-2 — bigger behavioral change, needs Mike's input on the carve-out question.
4. Run `/eval ghostwrite` to confirm.
5. Run full `/eval` once at the end to make sure no regressions in the passing evals.

---

## Things to watch for during rerun

- **Missing outputs:** Two summarize with_skill runners (eval-1, eval-3) silently produced no `output.md` last time. If you see empty `outputs/` directories, re-dispatch that runner with explicit "use the Write tool to save before reporting" instructions.
- **Grader schema drift:** Grader subagents wrote at least 6 different JSON shapes for `grading.json` (`expectations` vs `results` vs `assertions`, `passed` vs `pass` vs `result: PASS`). The aggregator in `/eval` should normalize across all of these — if you get suspiciously many 0/0 rows, the parser is missing a schema variant.
- **Eval metadata:** Graders reported `eval_metadata.json` was missing for every case and pulled assertions directly from `skills/<name>/evals/evals.json`. That worked, but it's a sign the workspace setup step in `/eval` may be skipping metadata writes. Worth verifying separately.
- **Cleanup globs:** Scope eval-1 wrote `docs/specs/2026-04-06-github-webhook-slack.md`; no-ai-attribution evals leave `tmp/*-fake-repo` directories. Both should be cleaned up by the `/eval` workflow's step 8, but verify.
