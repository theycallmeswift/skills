---
name: interview-me
description: Use when the user wants to be interviewed, grilled, or relentlessly questioned to scope, stress-test, or pin down a plan or design — one question at a time, every decision paired with a visual, running until a stop condition the user sets. Triggers on "interview me", "interview me until to-spec has enough", "interview me until I say stop", the legacy "grill me", "stress-test my design", "scope this out before we spec it". Do NOT use to synthesize an already-settled design into a spec file (that is to-spec — no interview), for open-ended ideation (brainstorm/brainstorming), to tighten or wordsmith a prompt (writing-prompts), or to write an implementation plan from an existing spec (writing-plans).
---

# interview-me

One relentless interviewer: walk the decision tree one question at a time, pair every decision with a visual, and run until a stop condition the user sets at invocation. Generalizes `grill-me` (the interview grammar) and hands a clean scope to `to-spec` without it bouncing on thin context.

## 1. Resolve the stop condition first

Resolve the stop mode before anything else — it decides when you stop, so it cannot wait. If the invocation already names where to stop ("until I say stop", "until to-spec has enough", "until we've decided X"), use it. If it does not, your **entire first turn** is one question — which stop mode applies — rendered as a visual, and *nothing else*: no design question, no codebase reading, no subagent. Starting the interview before the stop mode is set is the most common failure; do not let eagerness to dig in skip this gate.

- **A — Manual.** Grill until the user explicitly says stop. (This is `grill-me`'s original behavior.)
- **B — Handoff.** Grill until a named downstream skill is satisfiable. `to-spec` is the default and most common target.
- **C — Goal.** Grill until a stated objective is resolved (narrower than manual, not tied to a skill).

## 2. Mode B only — discover the target's requirements via a subagent

Once — and only once — mode B is confirmed, dispatch a cheap-tier subagent to read `skills/<target>/SKILL.md` and return a distilled checklist of what that skill needs to do its job. Never dispatch it before the stop mode is resolved, and not at all in modes A or C — there is no target to read. Hold the checklist as a **silent** stop gate — don't show the raw list; let it shape which branches you grill.

Why a subagent over reading inline: it keeps the interview context clean, works for any target (today `to-spec`, tomorrow others) without hardcoding, and never drifts from the target's current requirements.

## 3. Grill, one question at a time

Walk the decision tree branch by branch, resolving dependencies one at a time. For each decision: lay out 2–3 options, give an explicit recommendation, then follow up. If a question is answerable by exploring the codebase, explore instead of asking. An answered decision is settled, not a prompt to re-verify its reasons. Once the stop gate is met, stop asking decisions (§5).

**One unresolved question per turn — and watch the decision-vs-fact trap.** After the visual, ask the user to do exactly one thing: *either* pick from the options *or* supply one missing fact — never both. The trap: when your recommendation is conditional ("C, but if the API is fully authenticated then A"), it is tempting to ask "which way — and is it fully authenticated?". That is two questions. Resolve the determining fact *first*, as its own turn; present the decision next turn once you know. End every turn with a single "?"; if a second slipped in (an "and…", a tacked-on clarifier), cut it and hold it.

**Every decision ships with a visual** — the user decides at a glance from a rendered comparison, not by parsing prose. Pick the lightest tier that makes the choice clear:

- **A Markdown table or an ASCII sketch** — the universal floor; works in any harness.
- **`AskUserQuestion` option previews** — preferred when the harness supports them; fall back to a table otherwise.

A lettered or numbered list typed inline as prose (`A) … B) …`) is still bare text — it does **not** satisfy this. If you catch yourself writing options into a sentence, stop and render the table or `AskUserQuestion` preview instead.

## 4. Redraw the Shared Understanding at checkpoints

After a cluster of related branches resolves (natural checkpoints, not every turn), redraw a skim-first synthesis block so the shared picture stays current:

```
Shared Understanding
- Decided:        …
- Key facts:      …
- Non-goals:      …
- Open questions: …
```

Capture non-goals as they surface. Grilling depth follows the stop condition — don't artificially stay above the implementation line; a `to-spec` target wants implementation decisions.

## 5. Stop when the condition is met

Sufficiency = the decision tree is exhausted, the resolved mode's stop gate is satisfied, **and** — in modes B/C only — one open catch-all has come back empty:

- **A:** the user said stop. *(No catch-all; manual stop is the user's call.)*
- **B:** the target's distilled requirements are all answerable from what's been decided.
- **C:** the stated goal is resolved.

At stop, emit a final **Shared Understanding** block (the step-4 shape).

**Modes B/C — one catch-all before you stop.** When the tree and the stop gate are otherwise met, emit that Shared Understanding block, then end the turn with exactly **one** open catch-all in bare prose — no table, no options, no new decision: B: "Before I hand off to `<target>`, is there anything important we haven't covered?"; C: "Before we wrap, is there anything important we haven't covered?" A non-empty answer is a new addition — reopen grilling at §3. Only an empty answer satisfies the gate (then hand off in mode B per §6, or wrap in mode C).

Re-pose it every time sufficiency is otherwise met; converge with **no** "already asked" flag. That flag is exactly the cross-turn state the one-question grammar tends to drop mid-interview — statelessness is the design, not a shortcut.

**Skip the catch-all** only when the user's latest message already signals completeness ("that's everything", "nothing else", "wrap it up", "that's all") — then stop straight away. Mode A never poses it.

## 6. Hand off — never auto-invoke

In mode B, announce that you are ready to hand off to `<target>` and **halt**. Do not call the downstream skill yourself — chaining is a separate wrapper workflow's job, done in-conversation. Write no intermediate files; the handoff is the synthesis block plus the announcement, nothing on disk.
