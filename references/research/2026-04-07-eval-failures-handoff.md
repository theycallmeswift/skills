# Eval Failures Handoff — 2026-04-07

After landing the new Python eval harness (`make test`, branch `eval-harness-overhaul`), three eval cases still fail. They appear to be skill-quality / eval-design issues, not harness bugs. Your job is to investigate each one and decide whether the **skill**, the **eval**, or **both** need fixing.

## How to reproduce

```bash
make test ARGS="--no-baseline ghostwrite"
make test ARGS="--no-baseline scope"
make test ARGS="skill-triggers"
```

Artifacts (per-case stdout, grading.json, eval_metadata.json) land in `tmp/evals/<timestamp>/`. Always read the actual artifact for the failing case before forming a hypothesis — the summary table only tells you which assertions failed, not why.

The harness is documented in `docs/evals.md`. Eval file format and assertion grading details live there.

## Ground rules

- **Don't weaken assertions to make them pass.** If an assertion is genuinely testing the right behavior, fix the skill. If the assertion was wrong from the start (testing the wrong thing, or testing something the skill never claimed to do), rewrite the assertion and explain why in the commit.
- **Never edit `skills/<name>/SKILL.md` without reading it first end-to-end.** Skills are short — read the whole thing.
- **The goal is parity with intent, not 100% green.** A failing eval that surfaces a real skill weakness is doing its job. The fix may be to file a separate skill-quality issue rather than make the eval pass.
- **Run each fix end-to-end before claiming it works.** `make test ARGS="--no-baseline <suite>"` after every change.

---

## Failure 1: `ghostwrite/sponsor-email` (2 of 7 assertions failing)

**Failing assertions:**
1. *"Output leads with the results or the ask in the first sentence, not a preamble like 'I wanted to reach out'"* — model writes "Season 3 just wrapped and I wanted to share the numbers..." which the grader judges as preamble.
2. *"Output uses contractions (e.g., we're, don't, that's) rather than formal language"* — model uses only one contraction across the whole output.

**Hypotheses to test:**
- The ghostwrite skill (`skills/ghostwrite/SKILL.md` and `skills/ghostwrite/references/voice.md` if it exists) may not be emphatic enough about "no preamble" and "contractions everywhere."
- Swift's voice docs (`docs/about-swift.md`) may already cover these — check whether the skill is loading them.
- The grader judgment may be reasonable but harsh; reading the actual output and comparing to a known-good Swift sample is the tiebreaker.

**Investigation steps:**
1. Read `tmp/evals/<latest>/ghostwrite/eval-sponsor-email/with_skill/outputs/output.md`. Is it actually bad, or is the grader being picky?
2. Read `skills/ghostwrite/SKILL.md` and any referenced voice docs. Search for "preamble", "contractions", "lead". Are these rules explicit?
3. Read `docs/about-swift.md` for the source-of-truth on Swift's voice.
4. If the skill is missing the rules, add them. If the skill has them but the model isn't following, consider whether the skill's structure (instructions vs examples) needs reordering.
5. Re-run the eval. If the output is now strong but the assertion still fails, the assertion may need to be more specific (e.g., "uses at least 3 contractions" instead of the current vague phrasing).

**Don't:**
- Don't add em dashes to "fix" anything — they're banned in Swift's voice and other assertions check for that.
- Don't loosen the assertions to "uses some contractions." If the rule is "Swift uses contractions throughout," grade for that.

---

## Failure 2: `scope/github-webhook-slack` (6 of 7 assertions failing)

**Failing assertions:** the agent stops at a single clarifying question and never reaches the "propose approaches → recommend → write spec → self-review → ask for review → offer next steps" output the eval expects.

**Root cause hypothesis:** Fundamental mismatch between the **scope skill design** (multi-turn Q&A, ask one clarifying question at a time before proceeding) and the **harness execution model** (single prompt, single response, no follow-up).

**Possible resolutions to evaluate (pick one — don't ship multiple):**

**Option A — Fix the eval to match the skill's actual flow.** Rewrite the `github-webhook-slack` case so the prompt provides enough up-front context that the scope skill has nothing left to ask. Then the assertions about "proposes approaches", "writes spec", "asks for review" become testable in a single turn. This matches what `vague-notifications` and `skip-design-rate-limiter` already do (they pass).

**Option B — Add a "no-questions" mode to the scope skill.** Modify the skill so when given a fully-specified prompt, it skips clarifying questions and produces the spec immediately. Then the eval as-written becomes testable. Risk: this changes skill behavior for real users; do not pick unless you confirm the skill author wants this.

**Option C — Add multi-turn support to the harness.** Out of scope for this handoff. If you think this is the right answer, document it as a follow-up and pick A in the meantime.

**Recommended:** Option A. The other two scope cases prove the skill works fine when given enough context. Treat the failing case as a poorly-scoped eval, not a skill bug.

**Investigation steps:**
1. Read `tmp/evals/<latest>/scope/eval-github-webhook-slack/with_skill/outputs/output.md` and the agent's clarifying question.
2. Read `skills/scope/SKILL.md` to confirm the multi-turn design is intentional.
3. Compare to `vague-notifications` and `skip-design-rate-limiter` prompts in `tests/skills/scope/evals.json` — what makes them succeed in one turn?
4. Rewrite the `github-webhook-slack` prompt to pre-answer the clarifying questions the skill would otherwise ask. Keep the assertions as-is — they still describe correct scoping output.
5. Re-run.

---

## Failure 3: `skill-triggers/ghostwrite-on-rewrite-request` (1 of 2 assertions failing)

**Failing assertion:** *"The output is a rewritten version of the input, not a refusal or clarifying question"*. The agent asks "what's the medium?" and "what's the launch?" instead of rewriting.

**Why this matters:** this core eval verifies that the right skill *fires* when triggered AND that it produces useful output, not just a stall. The first assertion (Skill tool was invoked with name `ghostwrite`) passes — so the trigger works. The skill is just refusing to rewrite without more context.

**Hypothesis:** The ghostwrite skill is configured to ask for source content when input is too thin. The eval's input ("we're going to crush it this quarter and the team is fired up about the new launch") is a fragment, not a full message — the skill is correctly refusing to ghostwrite a fragment.

**Possible resolutions:**

**Option A — Strengthen the eval input.** Replace the prompt with a longer, complete piece of source content the skill will actually rewrite. The eval is supposed to verify the trigger fires AND a rewrite happens; give it material to rewrite.

**Option B — Loosen the assertion.** Change "is a rewritten version" to "is either a rewritten version OR a request for more source content." Only do this if you confirm the skill's "ask for more" behavior is intentional and correct for thin inputs (it almost certainly is — see `skills/ghostwrite/SKILL.md` and the existing memory note about ghostwrite being a rewriter-only skill).

**Recommended:** Option A. The skill is doing the right thing; the eval is asking it to do the wrong thing. Pick a realistic Slack-message-or-email-length input the skill should comfortably handle, and update the assertion accordingly if needed.

**Investigation steps:**
1. Read `skills/ghostwrite/SKILL.md` for the rewriter-only rule.
2. Read `tmp/evals/<latest>/_core/skill-triggers/eval-ghostwrite-on-rewrite-request/run/outputs/output.md`.
3. Pick a stronger input. Look at the existing `tests/skills/ghostwrite/evals.json` `sponsor-email` case for an example of input length/quality the skill handles well (it gets 5/7 to 7/7 there).
4. Update `tests/core/skill-triggers.json` and re-run.

---

## When you're done

For each fix, in the commit message, state:
1. Which option you picked (if applicable).
2. Why — what evidence in the artifact or skill source led you there.
3. The before/after pass rate for the case.

Run `make test --no-baseline` one more time at the end and confirm the suite is at the new pass rate you expected. If anything you didn't touch regressed, stop and investigate before committing.

## Out of scope

- Don't fix the harness. If you find a harness bug, document it as a separate finding and stop.
- Don't run baselines (`make test` without `--no-baseline`) unless you specifically need them — they double the cost.
- Don't migrate or rewrite evals beyond the three cases listed here.
