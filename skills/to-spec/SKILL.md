---
name: to-spec
description: Use whenever the user wants the design, decision, or discussion just reached in this session captured as a written design spec on disk — to spec, write up, draft, capture, or synthesize it into a skim-first spec file under docs/specs/. Fires on "capture this design as a spec", "write up the design we landed on", "turn our discussion into a design spec", "write this up as a design spec", "spec this out", "draft a spec from what we figured out", and PRD-migration phrasings like "turn this into a PRD" (to-spec owns the context→spec surface the retired to-prd had) — INCLUDING plain-task phrasings that name no skill. No interview. Do NOT use to author a skill (writing-agent-skills), wordsmith a prompt/context doc (writing-prompts), write an implementation plan from an existing spec (writing-plans), write a handoff doc (handoff), dump the conversation to a file (export-agent-session), or capture a source into the wiki as pages (ingest/archive). Not an OpenAPI or hardware spec.
---

# to-spec

Synthesize the conversation and codebase context already in hand into a skim-first design spec and write it to `docs/specs/`. Work from what's there — no interview, no runtime Q&A. Skim-first means narrative is a cost: labeled bullets over paragraphs, the artifact before the prose, a flow diagram carrying the structural load.

## Output location

Paths resolve against the project root — the current project directory interactively, or `PROJECT_ROOT` (then cwd) when scripted or run in an eval. The spec lands at `docs/specs/YYYY-MM-DD-<slug>.md`: today's date plus a kebab-case slug of the title, with **no** `-design` suffix (older specs carry one; new specs drop it).

## Procedure

1. **Gather context — don't interview.** Work from the conversation and codebase already in reach. Synthesize existing context; do not run a Q&A to design the thing (that's `grill-me`'s job — used to design a skill, not to run this one).

2. **Sufficiency gate.** Judge whether the context determines a spec. If it's too thin to ground one — a vague aspiration with no concrete problem, change, or constraints — stop: report specifically what's missing and hand the decision back to the user. Don't write a hollow spec, don't interview to fill the gap, don't silently redirect elsewhere. Gaps that merely under-determine *parts* of an otherwise-groundable spec are not this case — those go to `## Open Questions` (step 4).

3. **Draft from the template.** Copy `assets/spec-template.md` and fill every section; its inline comments carry the per-section rules. Delete each `<!-- … -->` comment as you fill it. Keep the section order and headings exactly.

4. **Ground perishable facts against the live tree — the gating step.** Current-state claims go stale and cost the most when wrong: `file:line` anchors, "X is hardcoded in Y", "first consumer of Z", "the stopgap to remove". Verify each against the actual files — read or grep them — never assert from conversation memory alone. Drop or correct any claim the tree contradicts. A claim the context can't settle goes to `## Open Questions`, phrased as open — not invented into Problem/Solution/Stories as confident prose.

5. **Self-review the draft before writing.** Scan for: leftover placeholders or TBD/TODO text and template comments; internal contradictions; ambiguity a reader couldn't resolve; scope too big for one spec (flag decomposition rather than burying it). Fix inline — no interview.

6. **Validate structure.** Where `python3` is available, run the linter and fix everything it flags:

   ```
   python3 scripts/validate_spec.py <path-to-draft>
   ```

   Where `python3` is absent (e.g. an eval sandbox), self-check against the same rules: a one-line TL;DR opener; every required section present — Problem, Solution, User Stories, Implementation Decisions, Testing Plan, Documentation Plan, Out of Scope, **References**, **Verification**; no empty section (including a present-but-empty `## Open Questions` — delete it if unused); no leftover placeholder text or template comments.

7. **Write the spec** to `docs/specs/YYYY-MM-DD-<slug>.md`. This is the terminal action — a file write. No network, no `gh`, no publishing; pushing the spec to a tracker is a separate future step.

## Testing Plan rule

Every emitted spec's Testing Plan is a **coverage contract, not a test manifest** — this holds for all specs:

- **Guarantees, not cases.** Each entry is an observable behavior or property the implementation must satisfy — never a named `test_*`, function, file path, or case count. A spec precedes its implementation plan; concrete tests there go stale here. Enumerating tests is the plan's job.
- **Surfaces derived per artifact, named by the question each answers** — `Logic` (isolated deterministic computation), `Behavior` (the artifact run for real, output observed end-to-end), `Interface` (the boundary the outside invokes or consumes it through). Instantiate Interface to the artifact: a skill → trigger routing; a service → API contract + authz; a CLI → args + exit codes; a library → consumer back-compat.
- **Pick only surfaces that apply.** Declare one N/A with a one-line reason rather than manufacturing an empty bucket. Append a cross-cutting surface (perf, security) only when the artifact's risk demands it.
- **No commands.** Runnable done-criteria (`make lint`, `make test`, scoped `make evals`) live under **Verification**. Testing Plan = *what* to guarantee; Verification = *how* it's checked.

## Notes

- **One spec per invocation.** Synthesize one coherent design; don't batch unrelated ones.
- **The diagram maps to real symbols.** Flow-diagram nodes correspond to real symbols, paths, or commands from the codebase, so the diagram doubles as the implementation skeleton.
- **`validate_spec.py` checks structure, not truth.** "Is this `file:line` real?" is semantic — that stays the grounding step (4) and review's job, never a regex.
