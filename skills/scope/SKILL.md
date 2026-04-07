---
name: scope
description: "Use when the user wants to scope, brainstorm, design, or think through an idea before building it. Triggers on requests like 'scope this', 'brainstorm', 'let's think through', 'help me design', 'what should I build', 'how should I approach', or any request to explore an idea before implementation. Also trigger when the user describes a project, feature, or system and hasn't started building yet. If the user jumps straight to implementation on something non-trivial, suggest scoping first. Use this skill before any creative work: creating features, building components, adding functionality, or modifying behavior."
---

# Scope

Turn ideas into fully formed designs through collaborative dialogue. Explore the idea, narrow the scope, propose approaches, and land on a spec the user approves before any implementation happens.

MechaSwift context (CLAUDE.md, about-swift.md) is already loaded, so you know the user's decision principles and voice. Apply them throughout: bias to action, concise over verbose, simple over clever, YAGNI ruthlessly.

## Hard Gate

Do not write any files (code, configs, specs, scaffolding, evals) until the user has explicitly approved a design. Reading existing files is fine. The spec in Step 6 is the first write, and only after Step 5 approval. "Present before persist", show the plan, get a yes, then write.

## Steps

1. **Explore project context** -- check files, docs, recent commits to understand the current state
2. **Ask clarifying questions** -- one at a time, understand purpose, constraints, and success criteria. Prefer multiple choice when possible. If the project is too large for a single spec, flag it and help decompose into sub-projects first.
3. **Propose 2-3 approaches** -- with trade-offs and your recommendation. Lead with the recommended option and explain why.
4. **Present design** -- in sections scaled to their complexity. A few sentences if straightforward, more detail if nuanced. Ask after each section whether it looks right.
5. **Get approval** -- explicitly ask the user to approve the design before writing anything. Do not proceed until they confirm.
6. **Write spec** -- save to `references/specs/YYYY-MM-DD-<topic>.md` using the Spec Template above. This is the first point where files are created. Do not commit unless the user asks.
7. **Spec self-review** -- scan for placeholders, contradictions, ambiguity, scope creep. Fix inline.
8. **User reviews spec** -- ask the user to review before proceeding
9. **Transition** -- offer the user options for what's next

## Spec Template

Use this skeleton for every spec. Scale each section to the project, short for simple work, longer for nuanced. Delete sections that genuinely don't apply, but default to keeping them.

````markdown
# <Topic>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved | Implemented

## Goal
One or two sentences. What are we building and why does it matter now?

## Non-Goals
What is explicitly out of scope. Prevents scope creep during implementation.

## Approach
The recommended approach in 2-5 sentences. Reference alternatives only if the trade-off matters.

## Components
Bullet list of the pieces being built or changed. One line each. Include file paths where known.

## Data / Interfaces
Any data shapes, function signatures, or external interfaces the implementer needs. Skip if trivial.

## Testing
How we'll know it works. What gets an eval, what gets a manual check, what is left unverified and why.

## Open Questions
Anything still unresolved. Empty is fine, but if you have unresolved items at write time, list them so the implementer can flag them.
````

## Clarifying Questions

- One question per message. Don't overwhelm.
- Multiple choice preferred over open-ended when possible.
- Focus on: purpose, constraints, success criteria, edge cases, dependencies.
- If scope is too big, stop and decompose before going deeper.

## Proposing Approaches

- Always propose 2-3 different approaches with trade-offs.
- Lead with your recommendation and explain why.
- Apply the user's decision principles: prefer the simplest approach that solves the problem. Don't propose over-engineered options for the sake of having three choices.

## Presenting the Design

- Scale each section to its complexity. Don't pad simple sections.
- Cover what's relevant: architecture, components, data flow, error handling, testing.
- Ask after each section if it looks right. Be ready to go back and revise.
- Design for isolation and clarity: small units, clear interfaces, testable independently.

## Working in Existing Codebases

- Explore the current structure before proposing changes. Follow existing patterns.
- If existing code has problems that affect the work, include targeted improvements in the design. Don't propose unrelated refactoring.

## Writing the Spec

Save the validated design to `references/specs/YYYY-MM-DD-<topic>.md`. Do not commit unless the user asks.

After writing, do a quick self-review:

1. **Placeholder scan:** Any TBD, TODO, or vague requirements? Fix them.
2. **Internal consistency:** Do sections contradict each other?
3. **Scope check:** Is this focused enough for a single implementation plan?
4. **Ambiguity check:** Could any requirement be interpreted two ways? Pick one and make it explicit.

Fix issues inline, then ask the user to review:

> "Spec written and committed to `<path>`. Take a look and let me know if you want to change anything before we move on."

## What's Next

After the user approves the spec, ask what they'd like to do:

1. **Write an implementation plan** -- invoke the writing-plans skill or equivalent to break the spec into actionable steps
2. **Scope another piece** -- if this is part of a larger project, start a new scoping session for the next sub-project
3. **Something else** -- the user decides

Don't assume the next step. Ask.
