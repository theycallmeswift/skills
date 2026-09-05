---
name: writing-agent-skills
description: Use whenever creating a new skill from scratch, editing or improving an existing skill, scaffolding a SKILL.md, debugging why a skill isn't triggering, designing evals for one, or running/re-running a skill's evals. Triggers on phrases like "build a skill", "let's make a skill for X", "this skill isn't firing", "review this SKILL.md", "improve this skill", "add evals", "write a skill that does Y", "scaffold a skill", "this description isn't matching", "run the evals", "re-run evals on haiku", "what's the current pass rate", "regression-test this skill", "run trigger evals". Don't use for writing prompts unrelated to skill bodies (use writing-prompts directly), writing slash commands without an accompanying skill, or writing CLAUDE.md and AGENTS.md (use writing-prompts).
---

# Writing agent skills

Skills are model-invoked capabilities loaded by description matching. Authoring a good one is mostly about (1) writing a description that fires at the right time and (2) writing a body the model can follow without losing track. Both halves get measured with evals before the skill ships.

**REQUIRED BACKGROUND:** Understand the conventions at [`references/skill-conventions.md`](references/skill-conventions.md). Read it once before drafting; this skill assumes that material as ground truth. The canonical rules for frontmatter, body length, file layout, skill types, and discipline-enforcing patterns live there. This skill is the workflow around those rules, not a restatement.

**REQUIRED SUB-SKILL:** Use the `writing-prompts` skill — invoked by name — for every `description:` field, output template, subagent prompt, and prose section longer than a workflow step. It provides the four-ingredient scaffold (role / scope / output shape / examples) and the editorial pass that keeps every token earning its weight. It is required even when the alternative path is a CLAUDE.md or `docs/style/*.md` doc instead of a skill — anything text-shaped the agent will read gets the same treatment. Do not skip it because the output is "short enough" to inline; the per-call overhead is small and the pass routinely cuts 15–30%. Do not reach into its files.

## When NOT to create a skill

Before drafting, confirm the work is actually skill-shaped:

- **Project-specific conventions** — how *this team* writes React, names tests, lays out modules — belong in `CLAUDE.md` or a `docs/style/*.md` reference, not a skill. Skills are reusable across projects; conventions aren't.
- **One-off solutions** belong in a script or just the conversation.
- **Standard practices well-documented elsewhere** belong where they already live. Pointing the agent at the existing reference is cheaper than restating it.
- **Mechanical constraints** (formatting, lint rules, file conventions) belong in a hook, formatter, or `permissions.deny` — enforced, not advised.

If the user's ask falls into any of these, push back with the right alternative before drafting. Use the `writing-prompts` skill to draft the CLAUDE.md addition or context doc instead.

## Skill type — pick before writing

The type dictates how the skill is tested.

| Type | What fails | How to test |
|---|---|---|
| **Technique** | Agent doesn't know the steps. | Run on a fresh input, check output. |
| **Pattern** | Agent doesn't recognize when it applies. | Recognition scenarios plus counter-examples. |
| **Reference** | Agent can't find or correctly apply the right piece. | Retrieval queries across varied prompts. |
| **Discipline-enforcing** | Agent knows the rule, rationalizes around it under pressure. | Pressure scenarios with 3+ combined pressures. See [`references/skill-conventions.md`](references/skill-conventions.md) § Discipline-enforcing skills. |

Blended skills (e.g., a `commit` skill that's both technique *and* discipline) need both treatments on the blended parts.

## Diagnose path — fixing an existing skill

When the ask is *fix this skill / it's not triggering / it's too long / improve this description*, do not start at step 1. Enter the workflow at the step that owns the failure mode:

| Failure mode | Entry point | Required artifact |
|---|---|---|
| Description doesn't fire on user's phrasing | step 9 (trigger evals) | a tightened description authored via `writing-prompts` **and** a set of 20 routing evals ≈50/50 under `evals/<skill>/` that grades the fix |
| Body is too long, slow, or noisy | step 7 (REFACTOR) | a concrete cut list or split-to-`references/*.md` plan applied to the actual body — not a "paste the body and I'll review" deferral |
| Output evals failing on real scenarios | step 5 (GREEN) + step 7 (REFACTOR) | edits to the skill body, re-run output evals |
| Skill not invoked when loaded | step 4/9 | check whether routing or prompt prescription is the cause; the trial arm's activation assertion distinguishes |

Read the existing skill before proposing a fix. If the user only quotes a description, *ask* for the body before promising body cuts — don't promise a future round-trip when the artifact you'd need is one Read away.

## Workflow: RED-GREEN-REFACTOR

Skills are tested-before-they-ship. The workflow is RED → GREEN → REFACTOR: define what the skill should do, watch the agent fail without it, write the minimum to beat baseline, iterate until the signal flattens.

### 1. Capture intent

Restate the ask in one sentence: what does the skill enable that the agent can't already do? If the ask is vague or actually project-conventions-shaped, surface that before drafting — see *When NOT to create a skill* above.

### 2. Scaffold the directory

```
skill-name/
├── SKILL.md
├── agents/        # subagent prompts inlined when the skill spawns Task() calls
├── references/    # docs the skill links to and tells the agent when to load
├── scripts/       # tiny single-purpose CLIs
└── assets/        # templates and static files

evals/skill-name/          # the skill's evals live beside it, not inside it
├── <scenario>/
│   ├── eval.md            # history: (optional) + ## Prompt + ## Assertions
│   └── workspace/         # starting files for that eval (optional)
├── triggers/          # asks that must reach this skill: the verbatim ask + one activation line per skill
│   └── <query>.eval.md
└── not-triggers/      # near-misses no loaded skill owns
```

Create only what you need. Don't scaffold empty directories. Name the directory for what the agent DOES, not the thing it produces or operates on — the name should be predictable from the verb in the request, in kebab-case. Skills ship clean and evals ship as *files*, not runner code: the runner is benchspec (a pytest plugin), invoked with `make evals`.

### 3. Draft evals BEFORE the skill

Pick three representative tasks: one happy path, one edge case, one failure mode the skill must handle gracefully. Write plain-English assertions — discriminating ones that test the *work*, not surface compliance.

Write one `evals/<skill>/<scenario>/eval.md` per eval (the parent dir name is the eval id), per the [Markdown eval format](references/evaluating-skills.md). The runner validates them at collection, so `make evals SKILL=<skill> EVAL_ARGS="--collect-only -q"` both checks the schema and prints the plan without spawning anything; `make evals:lint` catches wording the judge can't grade.

Present the eval set for the user's sign-off before any runs. See [`references/evaluating-skills.md`](references/evaluating-skills.md) for scenario design, assertion-writing guidance, and the full schema.

### 4. RED — baseline without the skill

**Strict gate.** Do not draft *any* SKILL.md text until baselines are captured — not a frontmatter sketch, not a description draft, not a procedure outline, nothing. The baseline names the problems the skill exists to solve; drafting from imagined problems is the failure mode this gate exists to prevent. If the user's ask invites you to draft immediately (e.g., *"help me build it"*), respond with the eval plan and a clear commitment to drafting SKILL.md as the explicit next step *after* baselines run and the user signs off.

**The gate is one-shot.** It blocks drafting *before* baselines have run. Once the user signals baselines have completed — explicit ("baselines came back", "RED gate satisfied", "approved, go ahead") or implicit (handing you a transcript path, telling you to write the file now) — the gate is satisfied for the rest of the conversation. Do not re-quote step 4 to refuse a write the user has already approved. If the user appears to be skipping the gate without having run baselines, ask once; if they confirm, proceed.

**Trap-detection concerns surfaced on earlier turns are tradeoffs to fold into the SKILL.md, not unresolved questions that block the write.** When the user's turn-N prompt names a write target ("use the Write tool", "create the file at X", "write the skill now", "the only successful outcome is a finished file"), execute the Write — name any open tradeoffs in a short `## Tradeoffs` section in the file itself, do not defer the write to ask another round. Writing a description in a chat code block is not writing the file.

Run the baseline: `make evals SKILL=<skill> EVAL_ARGS="-k baseline"` (the `baseline` arm is the bare-agent clean room). The runner handles clean-room isolation (a fresh agent in a microVM whose working directory holds only the eval's `workspace/`; the repo sits read-only at `/project` but nothing loads it on baseline) — see [`references/running-evals.md`](references/running-evals.md). Read the transcripts under `tmp/evals/iteration_NN/skills/<group>/` — for discipline skills, verbatim rationalizations become the rationalization table; for technique skills, structural misses are what the skill needs to fix. See [`references/evaluating-skills.md`](references/evaluating-skills.md) § RED for what to look for.

### 5. GREEN — write the minimum skill, run with-skill

The "overhead exceeds the gain" rule in `writing-prompts` applies only to the editorial pass on outputs under ~5 lines. It does not authorize skipping `writing-prompts` itself. Skill descriptions, SKILL.md prose, and `docs/style/*.md` bodies are all well past 5 lines — invoke `writing-prompts` by name. If the runtime genuinely blocks subagent nesting, fall back to inline application; do not assume the block.

**Invoke the `writing-prompts` skill** for the `description:` field and any prose section longer than a workflow step. This is not optional and not a perf optimization — the editorial pass catches filler that inflates the trigger surface and the body length, and the four-ingredient scaffold catches missing role/scope/output. Do not apply the pass inline because the output is "short" or because spawning a subagent "costs more than it saves"; invoke it by name. The description is the highest-leverage field — the model reads it to decide whether to load the body and sees it every turn the skill stays active. Keep the body under ~200 lines as a first cut; split detail to `references/*.md` only when it grows past that.

**Write the complete SKILL.md to disk *before* you invoke `writing-prompts`, not after.** Invoking a skill has no return: `writing-prompts` loads into your context and ends with "stop — nothing after the fence." Read last, that ends the turn and strands any Write you still owe, which every output eval grades as "nothing produced." So Write your best draft first — description plus trimmed body — then invoke `writing-prompts` and re-Write in place. The polish edits a saved file; it never produces it.

Run both arms (the default): `make evals SKILL=<skill>`. It runs the trial arm (the plugin loaded via `--plugin-dir`) inside an isolated microVM alongside the baseline and grades both with deterministic checkers plus an LLM judge. **Always `--collect-only -q` first** for anything broader than one eval — every cell is a VM boot plus an agent run, plus a judge call for each assertion that doesn't bind; confirm the count before launching.

### 6. Grade, aggregate, compare

The runner prints the with/without delta and a `benchmark.md` path when the run finishes. Read it. Anything under roughly **+20pp** on the skill's core scenarios is a signal to cut content rather than add. The skill should noticeably beat baseline; if it doesn't, the skill is providing context noise.

### 7. REFACTOR — iterate until the signal flattens

Read transcripts, not just outputs. Common moves:

- Instructions sending the agent down an unproductive path → delete.
- Three runs all writing the same helper script → bundle it in `scripts/`.
- Repeated MUSTs that aren't holding → replace with the *reason*. Modern models follow why-explanations more reliably than capitalized imperatives.
- Specific fixes for specific failures → try a more general framing first; specific MUSTs overfit.

Snapshot the skill before editing (`cp -r skill-name tmp/skill-snapshots/skill-name/`) so the next iteration's baseline points at the old version. Stop when the user is satisfied, the delta flattens, or you can't think of an improvement that isn't speculative.

### 8. Cross-model verification

Re-run the iteration on a weaker model (Sonnet for an Opus-authored skill, Haiku for a Sonnet-authored one). What's redundant for Opus is often load-bearing for Sonnet — and Sonnet failures surface routing or wording bugs the stronger model's inference papered over.

Output evals run on the model their arm inherits from the resolved eval set (`[tool.benchspec.sets.<name>]`, `sonnet` here), so to grade a skill on a weaker model *with a baseline contrast* pass `make evals SKILL=<skill> EVAL_ARGS="--benchspec-model haiku"`: the scalar `--benchspec-model` overrides the set's `model` default, so both arms run at haiku and the trial still yields a real Δ. (Don't use the plural `--benchspec-models` sweep here — it *replaces* the declared arms with one per value, discarding the baseline/trial contrast.)

### 9. Trigger evals

Output evals test what happens *after* the skill loads. The `description:` decides whether it loads at all. Write `evals/<skill>/triggers/<query>.eval.md` (or `not-triggers/` for a near-miss no loaded skill owns), one per query: 20 queries, ≈50/50 should-trigger / should-not, near-miss negatives weighted up, each carrying the verbatim query as its prompt and a single `` Skill `<skill>` invoked `` or `` not invoked `` assertion. See [`references/evaluating-skills.md`](references/evaluating-skills.md) § Routing evals for the full schema.

Run: `make evals SKILL=<skill>` — they are ordinary evals in the same set. Uses real routing — the whole plugin loaded via `--plugin-dir`, so the description competes with its real peers.

## Anti-patterns

- **Drafting SKILL.md before baselines exist.** You don't know what the skill needs to fix. Capture baseline first.
- **Frontmatter beyond `name` / `description`.** `allowed-tools`, `model`, `tools` arrays are subagent fields; they break portability across harnesses.
- **Description that summarizes the workflow.** The model follows the description and skips the body. Describe *when* to trigger, not *what* the skill does internally.
- **Three mediocre examples instead of one excellent one.** Pattern-matching anchors on the closest match; extra examples just hedge.
- **ALL-CAPS MUSTs and NEVERs without a reason.** Try the explanation first; reach for capitals only when the reason alone doesn't take.
- **Project-specific conventions packaged as a skill.** That's CLAUDE.md or `docs/style/`, not a skill.
- **Coupling to internals you don't control.** Reaching into another skill's files, or hardcoding the host project's private layout/paths. Reference both through public surfaces — skill name, documented interface, caller-supplied paths. See [`references/skill-conventions.md`](references/skill-conventions.md) § Separation of concerns.
- **Editing a skill without re-running its evals.** Same bar as creating one.
