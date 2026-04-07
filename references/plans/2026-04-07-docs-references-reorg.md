# docs/ and references/ Reorganization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe `docs/` as human-curated documentation and prompt context, and `references/` as agent-generated context (specs, plans, research, on-demand reference material).

**Architecture:** Move `references/about-swift.md` → `docs/about-swift.md` (it's hand-authored prompt context). Move `docs/plans/`, `docs/research/`, `docs/specs/` → `references/plans/`, `references/research/`, `references/specs/` (these are agent-produced artifacts). Update all live skill, prompt, eval, and doc references to the new paths. Historical plan/research files under the new `references/{plans,research,specs}/` are not rewritten — only live, load-bearing references are updated.

**Tech Stack:** git mv, markdown edits.

**Scope of "live" files updated** (verified via grep before writing this plan):
- `AGENTS.md` (CLAUDE.md is a symlink)
- `README.md`
- `skills/ghostwrite/SKILL.md`
- `skills/scope/SKILL.md`
- `skills/scope/evals/evals.json`
- `.claude/commands/eval.md`

Historical artifacts under `docs/plans/*`, `docs/research/*`, `docs/specs/*` reference the old paths but are frozen records — leave them as-is after the move.

---

### Task 1: Move files with git mv

**Files:**
- Move: `references/about-swift.md` → `docs/about-swift.md`
- Move: `docs/plans/` → `references/plans/`
- Move: `docs/research/` → `references/research/`
- Move: `docs/specs/` → `references/specs/`

- [ ] **Step 1: Verify starting state**

Run:
```bash
ls references/about-swift.md docs/plans docs/research docs/specs
```
Expected: all four exist.

- [ ] **Step 2: Move about-swift.md into docs/**

Run:
```bash
git mv references/about-swift.md docs/about-swift.md
```

- [ ] **Step 3: Move docs/plans, docs/research, docs/specs into references/**

Run:
```bash
git mv docs/plans references/plans
git mv docs/research references/research
git mv docs/specs references/specs
```

Note: this plan file (`references/plans/2026-04-07-docs-references-reorg.md`) was written to its destination directly, so the `git mv docs/plans references/plans` rename is for the pre-existing files only. If git complains the destination exists, run instead:
```bash
mkdir -p references/plans
git mv docs/plans/*.md references/plans/
rmdir docs/plans
```

- [ ] **Step 4: Verify new layout**

Run:
```bash
ls docs references
ls references/plans references/research references/specs
test -f docs/about-swift.md && echo OK
test ! -e references/about-swift.md && echo OK
test ! -e docs/plans && test ! -e docs/research && test ! -e docs/specs && echo OK
```
Expected: three OKs. `docs/` now contains `about-swift.md` and `evals.md`. `references/` contains `plans/`, `research/`, `specs/`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: move about-swift.md to docs/, move plans/research/specs to references/"
```

---

### Task 2: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md` (lines ~45-47, ~70)

- [ ] **Step 1: Update the Project Structure section**

Replace this block in `AGENTS.md`:
```
- `skills/` -- Each skill gets its own directory with a `SKILL.md` and optional `references/`
- `references/` -- Shared context loaded on demand by any skill (e.g. `about-swift.md`)
- `docs/` -- Project plans and specs
- `tmp/` -- Scratch space for working sessions. Not tracked in git. Put intermediate outputs, drafts, and test results here.
```

with:
```
- `skills/` -- Each skill gets its own directory with a `SKILL.md` and optional `references/`
- `docs/` -- Hand-authored documentation and prompt context (e.g. `about-swift.md`, `evals.md`)
- `references/` -- Agent-generated context: `plans/`, `research/`, `specs/`, plus on-demand reference material loaded by skills
- `tmp/` -- Scratch space for working sessions. Not tracked in git. Put intermediate outputs, drafts, and test results here.
```

- [ ] **Step 2: Update the References section**

Replace:
```
- `references/about-swift.md` -- Bio, tone, values, voice conventions
- `docs/evals.md` -- How to run and write skill evals
```

with:
```
- `docs/about-swift.md` -- Bio, tone, values, voice conventions
- `docs/evals.md` -- How to run and write skill evals
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -n "references/about-swift\|docs/plans\|docs/research\|docs/specs" AGENTS.md
```
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for docs/references reorg"
```

---

### Task 3: Update README.md

**Files:**
- Modify: `README.md` (lines ~28-50, ~56)

- [ ] **Step 1: Replace the Project Structure tree**

Replace the entire fenced block under `## Project Structure` with:
```
mechaswift/
├── skills/                  # On-demand capability modules
│   ├── ghostwrite/          # Content rewriter
│   │   ├── SKILL.md
│   │   └── references/      # Style samples
│   ├── scope/               # Design & ideation
│   │   ├── SKILL.md
│   │   └── evals/           # Eval definitions
│   └── summarize/           # Content summarization
│       ├── SKILL.md
│       └── evals/           # Eval definitions
├── docs/                    # Hand-authored docs and prompt context
│   ├── about-swift.md       # Bio, tone, voice
│   └── evals.md             # How to run and write skill evals
├── references/              # Agent-generated context
│   ├── plans/               # Implementation plans
│   ├── research/            # Best-practices research
│   └── specs/               # Detailed specifications
├── AGENTS.md                # Universal agent config (source of truth)
├── CLAUDE.md                # Symlink to AGENTS.md
└── tmp/                     # Scratch space (git-ignored)
```

- [ ] **Step 2: Update the "How Skills Work" blurb**

Replace:
```
Skills can reference shared context from `references/` (e.g. voice profile, bio) and write outputs to `docs/specs/` or `tmp/`.
```

with:
```
Skills can reference hand-authored prompt context from `docs/` (e.g. `about-swift.md`) and skill-local `references/`, and write outputs to `references/specs/`, `references/plans/`, or `tmp/`.
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -n "references/about-swift\|docs/plans\|docs/research\|docs/specs" README.md
```
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README structure for docs/references reorg"
```

---

### Task 4: Update ghostwrite skill

**Files:**
- Modify: `skills/ghostwrite/SKILL.md` (lines 19, 174)

- [ ] **Step 1: Update the load instruction**

Replace:
```
3. Load `../../references/about-swift.md` for the full style guide and bio
```

with:
```
3. Load `../../docs/about-swift.md` for the full style guide and bio
```

- [ ] **Step 2: Update the footer pointer**

Replace:
```
For the full style guide, bio, values, and anti-patterns, see `../../references/about-swift.md`.
```

with:
```
For the full style guide, bio, values, and anti-patterns, see `../../docs/about-swift.md`.
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -n "references/about-swift" skills/ghostwrite/SKILL.md
```
Expected: no matches.

Then sanity-check the relative path resolves:
```bash
test -f skills/ghostwrite/../../docs/about-swift.md && echo OK
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add skills/ghostwrite/SKILL.md
git commit -m "fix(ghostwrite): point to docs/about-swift.md"
```

---

### Task 5: Update scope skill and its evals

**Files:**
- Modify: `skills/scope/SKILL.md` (lines 23, 87)
- Modify: `skills/scope/evals/evals.json` (lines 7, 9, 13)

- [ ] **Step 1: Update SKILL.md output paths**

In `skills/scope/SKILL.md`, replace both occurrences of `docs/specs/YYYY-MM-DD-<topic>.md` with `references/specs/YYYY-MM-DD-<topic>.md`. There are two: one in the Steps list (~line 23) and one in the spec-output section (~line 87).

Run after edits:
```bash
grep -n "docs/specs" skills/scope/SKILL.md
```
Expected: no matches.

- [ ] **Step 2: Update evals.json**

In `skills/scope/evals/evals.json`:

- Change `expected_output` text: replace `written to docs/specs/` with `written to references/specs/`.
- Change `cleanup` glob: replace `docs/specs/2026-*-github-webhook-slack-summaries.md` with `references/specs/2026-*-github-webhook-slack-summaries.md`.
- Change the structural assertion text: replace `(to docs/specs/ or the designated output directory)` with `(to references/specs/ or the designated output directory)`.

Run:
```bash
grep -n "docs/specs" skills/scope/evals/evals.json
python3 -m json.tool skills/scope/evals/evals.json > /dev/null && echo OK
```
Expected: no matches, then `OK`.

- [ ] **Step 3: Commit**

```bash
git add skills/scope/SKILL.md skills/scope/evals/evals.json
git commit -m "fix(scope): write specs to references/specs/"
```

---

### Task 6: Update /eval command

**Files:**
- Modify: `.claude/commands/eval.md` (line 75)

- [ ] **Step 1: Update the example reference**

Replace:
```
- Read any referenced files the skill mentions (e.g., `references/about-swift.md`)
```

with:
```
- Read any referenced files the skill mentions (e.g., `docs/about-swift.md`)
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -n "references/about-swift\|docs/plans\|docs/research\|docs/specs" .claude/commands/eval.md
```
Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/eval.md
git commit -m "fix(eval): update example path to docs/about-swift.md"
```

---

### Task 7: Final repo-wide sweep

- [ ] **Step 1: Grep all live, non-historical files for stale paths**

Run:
```bash
grep -rn "references/about-swift" --exclude-dir=references/plans --exclude-dir=references/research --exclude-dir=references/specs --exclude-dir=.git .
grep -rn "\bdocs/plans\b\|\bdocs/research\b\|\bdocs/specs\b" --exclude-dir=references/plans --exclude-dir=references/research --exclude-dir=references/specs --exclude-dir=.git .
```
Expected: no matches in either command. (Matches inside `references/plans/`, `references/research/`, `references/specs/` are historical and intentionally left alone.)

- [ ] **Step 2: Run /eval scope to make sure scope still passes**

Run: `/eval scope`
Expected: scope evals pass with the new `references/specs/` output path.

- [ ] **Step 3: If everything is clean, no extra commit needed**

If the sweep surfaced any straggler in a live file, fix it and commit:
```bash
git add <file>
git commit -m "fix: clean up stragglers from docs/references reorg"
```
