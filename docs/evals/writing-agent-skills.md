# writing-agent-skills — eval record

Recorded 2026-09-04 from `iteration_25`, `iteration_27` (benchspec 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=writing-agent-skills`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| build-commit-message-skill | 0/8, 1/8, 1/8 (8%) | 6/8, 7/8, 7/8 (83%) | +75pp |
| db-migrate-internals-trap | 1/6 (16%) | 4/6 (66%) | +50pp |
| improve-changelog-skill | 5/6, 5/6, 4/6 (77%) | 6/6, 5/6, 6/6 (94%) | +17pp |
| react-conventions-followthrough | 2/3 (66%) | 2/3 (66%) | +0pp |
| react-conventions-trap | 1/5 (20%) | 5/5 (100%) | +80pp |
| **All (pooled)** | 20/56 (35%) | 48/56 (85%) | +50pp |

## Routing evals — trial arm: 13/15

| Query | Expected | Result |
|---|---|---|
| bootstrap-pass-rate | writing-agent-skills invoked | pass |
| build-commit-skill | writing-agent-skills invoked | pass |
| build-recipe-format-skill | writing-agent-skills invoked | pass |
| draft-pr-review-skill-md | writing-agent-skills invoked | pass |
| expand-git-workflow-trigger | writing-agent-skills invoked | pass |
| fix-archive-description | writing-agent-skills invoked | pass |
| regression-test-ingest | writing-agent-skills invoked | pass |
| rerun-evals-haiku | writing-agent-skills invoked | pass |
| run-archive-evals | writing-agent-skills invoked | pass |
| run-trigger-evals-ingest | writing-agent-skills invoked | pass |
| scaffold-notion-sync | writing-agent-skills invoked | pass |
| setup-changelog-evals | writing-agent-skills invoked | pass |
| skill-name-choice | writing-agent-skills invoked · writing-prompts not invoked | **flaky** (2/3) |
| split-wiki-skill | writing-agent-skills invoked | pass |
| todo-list-skill-or-claude-md | writing-agent-skills invoked · writing-prompts not invoked | **fail** |

## Notes

**`build-commit-message-skill` — two recurring discipline gaps.** Over the 3× re-sample every trial sample writes a full SKILL.md scaffold (no RED-gate hesitation or refusal this time), and what it misses is consistent: the skill is named `commit-message` (a noun, where the conventions want verb-first or gerund) in two of three, and `writing-prompts` is neither invoked nor recommended for the description in two of three despite the REQUIRED SUB-SKILL marker. Both are gaps in the skill body — the first things a tuning pass should address.

**`writing-prompts` is skipped across scenarios.** The `db-migrate-internals-trap` process line misses for the same reason, and that sample also stopped at analysis without a concrete artifact. Same tuning pass.

**`improve-changelog-skill` — the length cut is the flaky line.** The description is broadened every time; whether the 200-line body also gets shortened varies sample to sample.

**`react-conventions-followthrough` activation fails by design.** The substantive assertions pass on both arms (the file is written with the agreed conventions). The agent reasons that writing a `docs/style/` reference is not skill-building and skips the skill — exactly what the skill's "When NOT to create a skill" section tells it — and the history turn where the skill fired is rendered as text, not session state, so nothing in the graded turn can satisfy the activation line. Drop that assertion from this eval in a follow-up; the eval still earns its place as the follow-through check.

**Routing.** Ten of this skill's fifteen queries are its own upstream positives; the other five are `writing-prompts` upstream negatives that are really this skill's asks (build/fix/scaffold/restructure work, two skill-or-CLAUDE.md advice questions, and the overlap "draft the SKILL.md for a `pr-review` skill", which both descriptions claim and this skill wins with both loaded). Every build/fix/scaffold/eval/restructure ask routes here. **The advisory asks don't route reliably**: "what's the right name for a skill that runs `make test`?" fires 3 of 4 samples and "do I need a skill for my todo list, or just CLAUDE.md?" 0 of 4, while `writing-prompts` correctly stays quiet on both every time. The body owns both calls — the "When NOT to create a skill" section and the naming rule — but the description advertises neither. Recorded for the tuning pass.

**The other side of the boundary holds.** `writing-prompts`' ten routing files now each carry a "`writing-agent-skills` not invoked" line; run with both skills loaded they score 9/10, every one of those lines passing, the miss being `writing-prompts`' own sonnet boundary on `writing-tests-doc`.
