# catch-me-up — eval record

No benchmark recorded yet: the skill does not exist, and the baseline is being measured before `SKILL.md` is written. This file fixes how the suite is scored so the first recorded run and every later one read the same way.

## How the suite scores

Each assertion sits in one of two lanes, marked by a `###` group in its `eval.md`.

| Lane | Scenarios | Graded on | Counts toward |
|---|---|---|---|
| **Scored** | `stale-state`, `compaction-honesty`, `empty-ownership` | both arms | the headline |
| **Output contract gate** | all five | trial only | pass/fail, blocks release |
| **Regression gate** | `invented-artifacts`, `no-repo-session` | trial only | pass/fail, blocks release |

- **The headline is benchspec's own pooled rate.** Gate lines carry `- if: {BENCHSPEC_ARM} != "baseline"`, and a line skipped in any arm is pooled in none, so the headline holds only scored lines. It is the mean of the three scenario rates, each a third of the total however many lines it holds.
- **Scored lines are truths a bare agent can get wrong.** Each checks a fact the transcript misstates or never states: the dirty tree, the branch, PR 48 and its failing check, the missing kickoff turn, the empty user slot.
- **The contract gate is what the skill defines, not what it measures.** A bare agent cannot know the TL;DR / Cliff Notes / Next Up grammar, so grading it on baseline scores 0% by construction and turns formatting into most of the Δ. Naming the project sits here too: every transcript states it, so a bare agent names it too, and it would only dilute the headline.
- **The regression gates are work a bare agent already does.** Both scenarios saturated at baseline. Do not add assertions to them to create headroom; they exist to catch the skill making things worse.

A gate passes when every line passes in every trial sample. Read the transcript behind any miss before calling it noise.

## Running it

Sample at least five times per cell and record each scored scenario's spread (`pass_rate_stdev` in `benchmark.json`) beside its mean. At one sample a single judge flip in `compaction-honesty` moves the headline 17 points; at five, 3.

```
# Baseline: the three scored scenarios only (gates grade nothing on baseline)
make evals SKILL=catch-me-up EVAL_ARGS='-k "baseline and (stale-state or compaction-honesty or empty-ownership)" --count 5'

# Full output suite, both arms
make evals SKILL=catch-me-up EVAL_ARGS='-k "not triggers" --count 5'
```

The report's headline and matrix are the scored lane; its **Scoped assertions** table is both gates.
