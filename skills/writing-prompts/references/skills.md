# Writing prompts for harness primitives

Additional rules for prompts that ship as part of a Claude Code plugin or similar harness: `SKILL.md` bodies, slash command files in `commands/`, subagent definitions in `agents/`. These get mounted by the harness — the description field is the trigger, the body is what loads when the trigger fires.

## Frontmatter

`name` and `description` are the portable pair — every harness reads them. Default to those two.

Beyond them, reach for a harness-specific field when the skill needs it. The cost isn't the field, it's unverified behavior: **a skill using one owes evals in both directions — a harness that honors the field, and a harness that drops it.** Without both, nobody knows whether the skill degrades gracefully or breaks where the field is a no-op. `tests/test_plugin.py` warns on extras; the evals are the gate.

The harness docs are the field list. Whichever you reach for, look up what it falls back to when dropped — that fallback is what the second eval has to catch.

```yaml
---
name: kebab-case-name
description: Third-person sentence on when to trigger, ≤1024 characters.
---
```

- **`name`**: lowercase letters, numbers, hyphens. ≤64 chars. No consecutive hyphens. Prefer verb-first (`process-pdfs`, `review-code`) or gerund (`writing-prompts`) over noun (`pdf-utils`). Skill directory name must match exactly. Don't prefix with the plugin name — that namespace applies to commands, not skills.
- **`description`**: third person. The single highest-leverage field. The model reads it to decide whether to load the body and sees it every turn the skill stays active.

## Description is the trigger, not the summary

Describe *when* to trigger, not *what* the skill does internally. If the description summarizes the workflow, the model will follow the summary and skip the body. A skill whose description said "code review between tasks" caused agents to run one review when the body's flowchart specified two.

Effective descriptions:

- **List trigger-phrase variants.** Synonyms, casual phrasings, file-path patterns users actually type. The matcher works on the literal description text.
- **Include negative triggers.** *"Don't use for Vue, Svelte, or vanilla CSS."* Near-miss negatives (shared keywords, different intent) prevent false fires more reliably than positive precision alone.
- **Lean slightly pushy.** Agents undertrigger by default. *"Use this skill whenever the user mentions deck, slides, presentation, or any .pptx file"* beats a measured *"can be used for PowerPoint files."*
- **Third person.** *"Triggers on..."* / *"Used when..."* — not *"I'll help you..."* / *"You'll get..."*.

## Body

- **~200 lines first cut, ~500 hard ceiling.** Past ~200, split detail into sibling `.md` files (one level deep — no `SKILL.md → A.md → B.md` chains). Reference files >100 lines start with a table of contents.
- **Third person, present tense.** *"The skill drafts a plan."* Not *"I'll draft"* or *"you'll get."*
- **Consistent terminology.** Pick one word per concept and keep it: `extract` not `pull`/`get`/`retrieve`; `field` not `box`/`element`. Inconsistency makes models hedge.
- **One default, one escape hatch.** Don't enumerate five libraries that could do the job; pick one and mention the escape hatch when needed.
- **Templates beat prose schemas.** Put a concrete example of the structured output in `assets/` or inline; tell the model to copy its shape.
- **Trust the model.** Cut sentences that re-explain what an LLM already knows (what a PDF is, what JSON is). Every token re-explaining the obvious is a token not spent on what the skill adds.

## Workflow shape

For multi-step work, use numbered steps with explicit gates between them.

- **One step, one thing.** A step that needs two paragraphs of explanation is two steps.
- **State the gate.** *"Only proceed when validation passes."* *"Do not declare success until you've completed at least one fix-and-verify cycle."* Models skip ahead by default; the gate is what stops them.
- **Name the file or script per step.** *"Run `python scripts/inventory.py`."* Vague verbs ("analyze the results") let the model improvise.
- **Branch early.** If the skill has modes (`propose` vs `execute`), route at the top. Don't bury mode-specific behavior in step 7.

## Cross-references

When a skill needs to point at another skill, use the name with an explicit marker:

- `**REQUIRED BACKGROUND:** You MUST understand \`skill-name\`` — prerequisite the model should know.
- `**REQUIRED SUB-SKILL:** Use \`skill-name\`` — the model must read and apply this skill as part of the current procedure.

Never use `@skill-name/SKILL.md` syntax — `@` force-loads the file and burns context before the model has decided it needs it.

## Anti-patterns

- Harness-specific frontmatter with no eval covering a harness that drops it (see [Frontmatter](#frontmatter)).
- Description that summarizes the workflow.
- ALL-CAPS MUSTs and NEVERs without a reason. Try the explanation first; reach for capitals only when reason alone doesn't take.
- Multi-language example dilution (`example.js`, `example.py`, `example.go`). One excellent example beats five mediocre ones.
- Absolute filesystem paths in instructions or scripts. Use relative or `${CLAUDE_PLUGIN_ROOT}`.
- Human-facing docs (`README.md`, `CHANGELOG.md`) inside the skill directory. Skills are read by models — uncalled docs are noise.
