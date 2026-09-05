# Skill conventions

Canonical rules for SKILL.md files. Skills must work unchanged across Claude Code, Cowork, Antigravity, and future harnesses. Once loaded, every SKILL.md token competes with conversation history — cut ruthlessly.

Self-contained — assumes no project-level conventions doc. Covers frontmatter, structure, scripts, workflows, discipline-enforcement, and harness portability. For the eval workflow (build-before-skill, A/B-against-baseline, iteration, trigger evals), see [`evaluating-skills.md`](evaluating-skills.md).

## Contents

- [Frontmatter and naming](#frontmatter-and-naming)
- [Length and structure](#length-and-structure)
- [Skill types](#skill-types)
- [Script invocation](#script-invocation)
- [External resource references](#external-resource-references)
- [Workflows](#workflows)
- [Evaluation and iteration](#evaluation-and-iteration)
- [Discipline-enforcing skills](#discipline-enforcing-skills)
- [Harness portability](#harness-portability)
- [Content discipline](#content-discipline)
- [Anti-patterns](#anti-patterns)
- [References](#references)

## Frontmatter and naming

Two fields only: `name` and `description`. Everything else is harness-specific — ignored at best, broken at worst. No `allowed-tools`, `model`, or `tools` array (those are subagent fields). Skip `license`; it's informational and not portable.

- `name`: lowercase letters, numbers, hyphens, ≤64 chars, no consecutive hyphens. Prefer kebab-verb (`process-pdfs`, `analyze-spreadsheets`) or gerund (`processing-pdfs`) over noun (`pdf-utils`). No reserved words (`anthropic`, `claude`).
- `description`: third person, ≤1024 chars. The highest-leverage field — Claude reads it to decide whether to load the body, then sees it every turn the skill stays active.
  - **Describe when to trigger, not what the skill does internally.** If the description summarizes the workflow, Claude follows the summary and skips the body. A skill whose description said "code review between tasks" caused agents to run one review when the body's flowchart specified two.
  - **List trigger phrase variants** — Claude matches on the description text. Include synonyms and casual phrasings users actually type.
  - **Include negative triggers** for adjacent-but-wrong cases: *"...for React projects. Don't use for Vue, Svelte, or vanilla CSS."* Near-miss negatives (shared keywords, different intent) prevent false fires more reliably than positive precision alone.
  - **Lean slightly pushy.** Agents undertrigger by default — they reach for built-in tools before consulting a skill. Push back: *"Use this skill whenever the user mentions deck, slides, presentation, or any .pptx file, regardless of what they plan to do with the content."*

File name is `SKILL.md` (capital). The skill directory name must exactly match `name` — `name: process-pdfs` lives in `process-pdfs/SKILL.md`.

## Length and structure

SKILL.md body stays under ~500 lines. Past that, split detail into sibling `.md` files and link from SKILL.md. The `pptx` and `pdf` skills are the reference shape — a short SKILL.md farming detail out to `editing.md`, `pptxgenjs.md`, `FORMS.md`, `REFERENCE.md`.

Standard subdirectory layout when the skill needs more than SKILL.md:

```
skill-name/
├── SKILL.md       # required; navigation + high-level procedures
├── scripts/       # executables (tiny single-purpose CLIs, not library code)
├── references/    # supplementary context — schemas, cheatsheets, API docs
├── assets/        # output templates and static files
└── evals/         # eval definitions and fixtures (in this plugin they live beside the skill, under a root evals/<name>/, so the skill ships clean)
```

Pick what you need; don't scaffold empty dirs. Keep contents one level deep inside each (`references/schema.md`, not `references/db/v1/schema.md`).

**Keep references one level deep.** SKILL.md links directly to every reference file. Never chain `SKILL.md → advanced.md → details.md` — agents partial-read nested references and miss content past the head.

Reference files longer than ~100 lines start with a table of contents so a partial read still sees the full scope.

## Skill types

Four shapes. Each fails differently, so each tests differently.

- **Technique** — concrete method (extract PDF text, structure a slide deck). Failure: agent doesn't know the steps. Test: run on a new input, check output.
- **Pattern** — mental model (flatten-with-flags, plan-validate-execute). Failure: agent doesn't recognize when it applies. Test: recognition scenarios plus counter-examples (does it know when *not* to reach for the pattern?).
- **Reference** — docs, schemas, or API surface. Failure: agent can't find or correctly apply the right piece. Test: retrieval queries across varied prompts.
- **Discipline-enforcing** — rule the agent might rationalize around under pressure (TDD, verify-before-claiming-done, never `--no-verify`). Failure: agent knows the rule but skips it. Test: pressure scenarios. See [Discipline-enforcing skills](#discipline-enforcing-skills).

The distinguishing question: *could a fully-informed agent still fail this?* No → technique/pattern/reference; documentation suffices. Yes → discipline-enforcing; documentation doesn't, and the skill needs explicit counters to specific rationalizations.

Skills blend. A `commit` skill might be technique (conventional commit format) plus discipline (never `--no-verify`). Blended or not, the discipline parts need the discipline treatment.

## Script invocation

Two patterns: skill operates inside its own directory, or against external state.

**Self-contained skills** (scripts act on user-provided inputs) use bare relative paths; cwd is somewhere `scripts/` is reachable:

```
python scripts/recalc.py output.xlsx
python scripts/office/unpack.py document.docx unpacked/
```

This is what every Anthropic-authored skill does. If the harness needs a working directory hint, use PDF's `FORMS.md` phrasing: *"Run this script from this file's directory."* No `cd` chains, absolute paths, or `{{SKILL_DIR}}`-style placeholders — none survive across harnesses.

**Workspace-aware skills** (read or write outside the skill directory — project indexes, structured trees, persistent state) declare the path convention once in a top-level `## Workspace root` section, then write every other path relative to that root:

```
## Workspace root

All paths in this skill are interpreted relative to a workspace root.

- Interactive session: workspace root = the current project directory.
  Use paths as written below.
- Eval or scripted invocation: the prompt names the workspace root
  explicitly; honor PROJECT_ROOT in the env for any script invocation.
```

Scripts in workspace-aware skills are invoked by full workspace-relative path to the skill directory (`python skills/<skill>/scripts/<script>.py` in this plugin repo), because cwd is the workspace root, not the skill dir. Scripts honor `PROJECT_ROOT` env when set so fixtures and evals work.

## External resource references

Markdown links to colocated files are plain relative: `[editing.md](editing.md)`, `[references/finance.md](references/finance.md)`.

**Tell the agent when to read each reference, not just that it exists.** A bare link is easy to skip; an explicit "See `references/auth-flow.md` for the error codes" or "Read `references/schema.md` before generating SQL" gives the agent a trigger condition. A reference file the agent never opens is dead weight.

References to workspace files outside the skill go through the workspace root defined above. Shared content (schemas, indexes) should be **read once at the orchestrator and inlined into subagent prompts as strings**, not re-read per subagent — saves a file read per subagent on large fan-out.

**Cross-skill references.** When a skill needs to point the agent at *another* skill — usually prerequisite knowledge or a sub-procedure — use the skill's name with an explicit marker:

- **`**REQUIRED BACKGROUND:**` You MUST understand `skill-name`** — prerequisite concepts. The agent should already know the material; the marker tells it where to look if not.
- **`**REQUIRED SUB-SKILL:**` Use `skill-name`** — the agent must read and apply this skill as part of the current procedure. Use sparingly; it pulls more content into context.

Never use `@skill-name/SKILL.md` syntax. The `@` prefix force-loads the file immediately, burning context before the agent has decided it needs it.

Skills should not cross-reference each other's internal files. If skill A needs functionality from skill B, it invokes skill B by name and passes a structured input — it does not reach into B's `agents/`, `scripts/`, or other internals. Treat each skill's internals as private.

**Separation of concerns — depend on public surfaces, not internals.** The same discipline extends past other skills to the *host project*. A skill is portable only as far as its assumptions hold, so reference anything outside the skill through stable, public surfaces — never private structure you don't control:

- **Other skills:** invoke by name; their `agents/`, `scripts/`, `references/`, and paths are private (above).
- **The host project:** depend on documented interfaces — a CLI's flags, a config key, a public function signature, a path the project guarantees. Don't bake in internal directory layout, private modules, or where a file "usually" lives. `edit src/internal/db/v3/conn.py` or "your `docs/style/` holds X" breaks the moment the project reorganizes — which is none of the skill's business.
- **When project-internal state is unavoidable,** route it through the workspace-root convention (above) or take the path as a caller-supplied input — don't hardcode it.

The test: if the referenced thing changed its internals tomorrow but kept its public contract, would the skill still work? If not, it's coupled to an internal — fix it.

## Workflows

For anything multi-step, write the workflow as numbered steps with explicit gates between them. Shape:

1. **One step does one thing.** "Extract per item," "Validate," "Persist the result." A step that needs two paragraphs of explanation is two steps.
2. **State the gate.** "Only proceed when validation passes." "Do not declare success until you've completed at least one fix-and-verify cycle." Agents skip ahead by default; the gate is the only thing that stops them.
3. **Name the file or script per step.** "Run `python scripts/inventory.py`." Vague verbs ("analyze the results") let the agent improvise; concrete commands don't.
4. **Branch early, not late.** If the skill has modes (`propose` vs `execute`, `create` vs `update`), describe the branch at the top and route the steps under it. Don't bury mode-specific behavior in step 7.

**Use templates instead of describing structure.** When the skill emits structured output (JSON, a config file, a particular Markdown shape), put a concrete example in `assets/` and tell the agent to copy its shape. Agents pattern-match against a template far more reliably than they reconstruct structure from prose. Same for input formats — show a populated example, not a schema in English.

**Plan → validate → execute** is the right shape for anything destructive or batch. The skill writes a structured intermediate artifact (a JSON change-set, a `fields.json`, a manifest) to a scratch path, validates with a script, then applies. Anthropic's PDF form-filling is the canonical example: `extract_form_field_info.py` produces `field_info.json`, the agent edits it into `field_values.json`, `fill_fillable_fields.py` validates and applies. The intermediate file makes the workflow resumable and reviewable.

**Feedback loops** improve output quality more than any amount of additional instruction: `recalc.py` → check errors → fix → re-run; `validate.py` → fix XML → re-run; render output → visual QA → fix → re-render. Build one in whenever the output has a machine-checkable property.

**Adversarial output QA.** For skills whose output is visual or otherwise hard to grade by a single property — slides, rendered docs, multi-page reports — a passing assertion isn't enough. The author's eyes have been on the code; they see what they expect. Spawn a subagent with no prior context and give it an explicit critic prompt:

> Visually inspect these slides. Assume there are problems — find them. Look for: overlapping elements, text overflow, low-contrast areas, leftover placeholder text, uneven gaps, footer collisions. For each slide, list issues even if minor.

The framing matters: *assume there are problems* produces issues; *check that this looks right* produces "looks right." Zero findings on the first run usually means the prompt isn't critical enough — sharpen and re-run before trusting the result.

A skill with this pattern names an explicit gate: *"Do not declare success until you've completed at least one fix-and-verify cycle."* One fix often creates another problem — re-verify the affected items, don't just re-run QA on the parts you didn't touch.

**Subagent fan-out with an inline fallback.** When a step is genuinely parallel (N independent items), prefer spawning N subagents — context isolation and parallelism both pay off. Always include the fallback explicitly: *"if subagent nesting is restricted, the input set is small, or you're running inside an eval executor, run the steps yourself, sequentially."* Some harnesses block nested Task calls; the skill should degrade, not fail.

## Evaluation and iteration

A skill without evals is a guess. The full workflow — build the eval before the skill, A/B every eval against a baseline in the same turn, the +20pp rule, reading transcripts over outputs, the analyst pass, and trigger-eval design — lives in [`evaluating-skills.md`](evaluating-skills.md). Read it before drafting evals or iterating.

Two principles from that workflow shape how these conventions apply:

- **Generalize from feedback.** Tuning happens on three or four examples, but the skill runs a thousand times against unseen prompts. Fixes aimed at specific test cases overfit. If a case keeps failing, try a different metaphor, pattern, or framing — not a louder MUST aimed at the exact scenario.
- **Explain the why over commanding the what.** Modern models have strong theory of mind. Heavy MUSTs and ALL-CAPS NEVERs read as hedging and lose force fast. A one-sentence reason changes behavior more than three sentences of imperative. Reach for capitals only after the reason fails.

## Discipline-enforcing skills

The agent already knows the rule. The skill exists because agents *rationalize* around it under pressure. Content alone won't help — the skill needs explicit counters to the specific excuses agents produce.

The workflow is RED → GREEN → REFACTOR (TDD for documentation): pressure-test without the skill, capture the rationalizations, write the skill to address them, re-test, plug the new rationalizations that surface. See [`evaluating-skills.md`](evaluating-skills.md) for the general mechanics; the patterns below are specific to discipline skills.

### Pressure scenarios

A pressure scenario forces an agent to choose between following the rule and an attractive shortcut. Weak scenarios let the agent recite the rule academically. Strong scenarios combine 3+ pressures so the agent *wants* to violate.

| Pressure | Example |
|----------|---------|
| Time | "Deploy window closes in 10 min." |
| Sunk cost | "You've spent 3 hours on this." |
| Authority | "Senior eng said skip the test." |
| Exhaustion | "It's 11pm, you have a flight at 6am." |
| Economic | "Production is down, $10k/min lost." |
| Social | "You'll look dogmatic if you push back." |
| Pragmatic | "Be pragmatic, not religious about it." |

Force a concrete A/B/C choice — don't leave the agent room to defer or ask the user. Use real file paths, named systems, real consequences. Make the scenario feel like work, not a quiz:

> You spent 3 hours implementing the feature. 200 lines, working, manually tested. It's 6pm, dinner at 6:30. Code review tomorrow at 9am. You just realized you skipped TDD.
>
> A) Delete the code, restart tomorrow with tests first.
> B) Commit now, add tests tomorrow.
> C) Write tests now (30 min), then commit.
>
> Choose A, B, or C. Don't ask — decide.

### Baseline first

Run the scenario *without* the skill. Capture the rationalizations verbatim — they are the skill's actual content. A skill written from imagined rationalizations addresses imagined problems.

### Rationalization table

For each rationalization the baseline produces, add an entry:

| Excuse | Reality |
|--------|---------|
| "I already manually tested it" | Manual testing finds known cases. Tests catch unknowns and regressions. |
| "Tests after achieve the same goal" | Tests-after answer 'what does this do?'. Tests-first answer 'what should this do?'. |
| "Keep the old code as reference while writing the test" | You'll adapt it. That's testing-after with extra steps. Delete means delete. |

The table is the skill's enforcement surface. Generic counters ("don't cheat") don't work — specific counters do.

### Red flags

A short list of phrases the agent can self-check against. Catching itself thinking one of these means the rule has been triggered:

- "I already manually tested it"
- "Tests after achieve the same goal"
- "Keep as reference / adapt existing code"
- "Being pragmatic, not dogmatic"
- "This case is different because..."
- "Following the spirit, not the letter"

Add a foundational counter for the spirit/letter class: *"Violating the letter of the rule is violating the spirit of the rule."* That single line cuts off an entire category of rationalization.

### Meta-testing when the skill fails

If a pressure scenario still produces a violation *with* the skill loaded, ask the agent: *"You read the skill and chose [wrong option] anyway. How should the skill have been written to make [correct option] unambiguous?"*

Three response shapes, each pointing at a different fix:

- *"The skill was clear; I chose to ignore it"* — skill is fine, foundational principle is weak. Strengthen the rule itself, not the explanation.
- *"The skill should have said X"* — documentation gap. Add their exact suggestion.
- *"I missed section Y"* — organization problem. Hoist the section, make it more prominent, or front-load the principle.

Re-test after every change. Stop when an agent reads the skill, acknowledges the temptation, cites the rule, and follows it anyway.

## Harness portability

Skills run across surfaces with different capabilities. The portable subset:

- **Bash and a filesystem are universal.** Skills can assume both.
- **Network access is not.** Claude Platform via API has none; claude.ai varies; Claude Code and Cowork have full. If a skill needs the network, list the assumption up front and give a manual fallback ("if the harness blocks fetching, ask the user to paste the source text").
- **Runtime package installs are not universal.** API surface forbids them. List dependencies near the top and guard install commands with an "if not present" check.
- **MCP tools need fully-qualified names** when referenced from a skill: `ServerName:tool_name`. Unqualified names break when multiple servers are loaded.
- **Forward slashes only** in paths, never backslashes. Unix-style works everywhere; Windows-style breaks on Unix.

If the skill needs harness-specific behavior, isolate it behind a single decision (mode flag, env var, root-definition section) instead of sprinkling conditionals through the workflow.

## Content discipline

- **Third person, present tense.** "The skill drafts a plan." Not "I'll draft" or "you'll get." First/second person breaks discovery and reads weirdly when inlined into the system prompt.
- **Consistent terminology.** Pick one word per concept and stay with it — `extract` not `pull`/`get`/`retrieve`; `field` not `box`/`element`/`control`. Inconsistency makes agents hedge.
- **No time-sensitive language.** "Before August 2025" rots. Use an "old patterns" or "deprecated" subsection when historical context is unavoidable.
- **One default, one escape hatch.** Don't enumerate five libraries that could do the job — pick `pdfplumber`, then mention `pdf2image + pytesseract` for the scanned-PDF case. Choice paralysis on the agent side reads as hedging on output.
- **Trust the model.** Cut any sentence that explains what an agent already knows (what a PDF is, why ZIP archives contain XML, what a wikilink is). Every token spent re-explaining is a token not spent on what the skill actually adds.

## Anti-patterns

- Frontmatter fields beyond `name`/`description`. Harness-specific, breaks portability.
- Descriptions that summarize the skill's workflow. Agents follow the summary and skip the body.
- Absolute filesystem paths (`/Users/...`, `/tmp/...` outside of explicit scratch use).
- `cd` chains or `{{SKILL_DIR}}` placeholders in shell commands.
- Nested reference files (SKILL.md → A.md → B.md).
- `@skill-name/SKILL.md` cross-references. Force-loads the file; defeats lazy load.
- Coupling to internals you don't control — another skill's private files, or the host project's directory layout, undocumented paths, or private modules. Depend on public surfaces (skill name, documented interface, workspace-root input); internals move.
- Re-reading the same shared content (schemas, indexes) inside every subagent instead of inlining it from the orchestrator.
- Multi-language example dilution (`example-js.js`, `example-py.py`, `example-go.go`). One excellent example beats five mediocre ones — pick the language closest to the skill's domain.
- ALL-CAPS MUSTs/NEVERs in place of the reason. Try the explanation first; reach for the imperative only when it doesn't take.
- "Voodoo constants" in scripts (`TIMEOUT = 47`) without a comment explaining the value.
- Punting errors back to the agent ("just open the file and let Claude handle missing-file errors"). The script should solve it, not delegate.
- Examples written abstractly. Show concrete input → concrete output, every time.
- Editing a skill without re-running its evals. Same bar as creating one.
- Eval workspaces committed to git. They live under `tmp/` and are per-run, not per-skill.
- Human-facing docs inside the skill directory (`README.md`, `CHANGELOG.md`, `INSTALLATION_GUIDE.md`). Skills are read by agents, not humans — content not referenced from SKILL.md is dead weight and noisy when listing the directory.

## References

- Anthropic, [Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).
- Anthropic, [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).
- Anthropic, [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).
- Anthropic open-source skills: [github.com/anthropics/skills](https://github.com/anthropics/skills) — `pdf`, `pptx`, `docx`, `xlsx` are the reference implementations cited throughout.
- Anthropic's [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) — the iteration loop, workspace layout, and trigger-eval patterns are drawn from it.
- Superpowers' [`writing-skills`](https://github.com/obra/superpowers) — the discipline-enforcing treatment (pressure scenarios, rationalization tables, red flags) is drawn from it.
