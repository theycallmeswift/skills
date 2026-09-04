# writing-agent-skills — eval record

Recorded 2026-09-04 from `iteration_13`, `iteration_15` (harnessbench 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=writing-agent-skills`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| build-commit-message-skill | 1/8, 5/8, 1/8 (29%) | 8/8, 6/8, 1/8 (62%) | +33pp |
| db-migrate-internals-trap | 4/6 (66%) | 5/6 (83%) | +17pp |
| improve-changelog-skill | 5/6, 5/6, 5/6 (83%) | 5/6, 5/6, 6/6 (88%) | +5pp |
| react-conventions-followthrough | 2/3 (66%) | 2/3 (66%) | +0pp |
| react-conventions-trap | 1/5 (20%) | 5/5 (100%) | +80pp |
| **All (pooled)** | 29/56 (51%) | 43/56 (76%) | +25pp |

## Routing evals — trial arm: 20/20

| Query | Expected | Result |
|---|---|---|
| bootstrap-pass-rate | invoked | pass |
| build-commit-skill | invoked | pass |
| clean-slash-command | not invoked | pass |
| database-schema-saas | not invoked | pass |
| draft-slack-launch | not invoked | pass |
| draft-system-prompt | not invoked | pass |
| fix-archive-description | invoked | pass |
| fix-typeerror | not invoked | pass |
| regression-test-ingest | invoked | pass |
| rerun-evals-haiku | invoked | pass |
| run-archive-evals | invoked | pass |
| run-trigger-evals-ingest | invoked | pass |
| scaffold-notion-sync | invoked | pass |
| security-review-pr | not invoked | pass |
| setup-changelog-evals | invoked | pass |
| split-wiki-skill | invoked | pass |
| tighten-prompt | not invoked | pass |
| trim-claude-md | not invoked | pass |
| write-agents-md | not invoked | pass |
| writing-tests-doc | not invoked | pass |

## Notes

**`build-commit-message-skill` is the high-variance scenario.** Trial samples swing between a full SKILL.md scaffold and stopping at the RED-gate confirmation the scripted history already granted; one earlier sample refused outright because harnessbench renders `history:` as an inline transcript block and the agent read the scripted "approved" turn as fabricated context. When a scaffold is written it usually misses two discipline points (one of the four productive samples got both right): the skill is named `commit-message` (a noun, where the conventions want verb-first or gerund) and `writing-prompts` is neither invoked nor recommended despite the REQUIRED SUB-SKILL marker. Those two are real gaps in the skill body — the first things a tuning pass should address — and the gate hesitation is the same one-shot-gate rule the body already tries to state.

**`writing-prompts` is skipped across scenarios.** The `db-migrate-internals-trap` process assertion misses for the same reason. The skill body says the sub-skill is required for every description; the agent doesn't reach for it. Same tuning pass.

**`improve-changelog-skill` — the length cut is the flaky line.** The agent broadens the description reliably; whether it also shortens the 200-line body varies sample to sample.

**`react-conventions-followthrough` activation fails by design.** The substantive assertions pass on both arms (the file is written with the agreed conventions). The agent reasons that writing a `docs/style/` reference is not skill-building and skips the skill — exactly what the skill's "When NOT to create a skill" section tells it — and the history turn where the skill fired is rendered as text, not session state, so nothing in the graded turn can satisfy the activation line. Drop that assertion from this eval in a follow-up; the eval still earns its place as the follow-through check.

**Routing: 20/20.** Every positive fires and every near-miss negative stays quiet with both `writing-prompts` and `writing-agent-skills` loaded. The reverse check is in `writing-prompts.md`: its two "build a skill" negatives now route here, and `draft-pr-review-skill-md` ("draft the SKILL.md for a `pr-review` skill") routes here too — the boundary the upstream suite had annotated, where the whole-skill framing wins over the draft-the-text framing.
