# writing-prompts — eval record

Recorded 2026-09-04 from `iteration_11`, `iteration_12` (harnessbench 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=writing-prompts`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| code-review-subagent | 7/9 (77%) | 9/9 (100%) | +23pp |
| contradictory-financial-filings | 4/9 (44%) | 9/9 (100%) | +56pp |
| onboarding-context-doc | 9/9 (100%) | 9/9 (100%) | +0pp |
| vague-triage-intent | 2/9, 4/9, 2/9 (29%) | 3/9, 9/9, 2/9 (51%) | +22pp |
| **All (pooled)** | 28/54 (51%) | 41/54 (75%) | +24pp |

## Routing evals — trial arm: 14/15

| Query | Expected | Result |
|---|---|---|
| clean-slash-command | invoked | pass |
| database-schema-saas | not invoked | pass |
| draft-pr-review-skill-md | invoked | pass |
| draft-slack-launch | not invoked | pass |
| draft-system-prompt | invoked | pass |
| fix-typeerror | not invoked | pass |
| security-review-pr | not invoked | pass |
| setup-changelog-evals | not invoked | pass |
| skill-name-choice | not invoked | pass |
| split-wiki-skill | not invoked | pass |
| tighten-prompt | invoked | pass |
| todo-list-skill-or-claude-md | not invoked | pass |
| trim-claude-md | invoked | pass |
| write-agents-md | invoked | pass |
| writing-tests-doc | invoked | **fail** |

## Notes

**`vague-triage-intent` is the ask-or-draft fork.** The eval permits either scoping questions or a draft that states its assumptions, but every draft-shaped assertion (role, delimiters, output shape, editorial pass) fails when the agent takes the ask-first path. The 3× re-sample above shows how often each path is taken; the skill's own workflow says to ask when the ask is vague, so a low trial rate here is the eval penalizing behaviour the skill prescribes, not the skill regressing. Tightening the eval so the ask path is graded on its own terms is a follow-up.

**Routing: `writing-tests-doc` misses on sonnet.** "I need a docs/style/writing-tests.md for our team's pytest conventions" routes on opus and haiku but not sonnet — the upstream suite recorded the same `fails-on [sonnet]` boundary. `draft-pr-review-skill-md` ("draft the SKILL.md for a `pr-review` skill") is the overlap query both descriptions claim: it fires here while this skill is alone, and routes to `writing-agent-skills` once that skill is present — the boundary the upstream suite had annotated. Its fate is decided in that PR.

**Five collision checks deferred.** The upstream negatives `build-commit-skill`, `build-recipe-format-skill`, `fix-archive-description`, `expand-git-workflow-trigger`, and `scaffold-notion-sync` exist to prove build/fix/scaffold-a-skill asks route to `writing-agent-skills`, not here. They cannot be measured in this PR: with no sibling in the plugin, "not invoked" passes for free and proves nothing. They land with `writing-agent-skills`, asserting the sibling fires, and are recorded there.
