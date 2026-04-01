# MechaSwift v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship MechaSwift as a working Claude Code plugin with a ghostwriting skill and Gemini CLI compatibility.

**Architecture:** Claude Code plugin (`.claude-plugin/plugin.json`) with skills discovered via `skills/` directory convention. AGENTS.md is the source of truth for cross-platform config; CLAUDE.md is a symlink. The ghostwriting skill uses a reference file for the voice profile.

**Tech Stack:** Markdown, JSON (plugin manifest), no runtime dependencies.

**Spec:** `docs/plans/2026-04-01-project-plan.md`

---

### Task 1: Plugin Manifest

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Create the plugin manifest**

```json
{
  "name": "mechaswift",
  "description": "Mike Swift's personal agent framework — skills, configuration, and workflows for Claude Code, Claude Cowork, and Gemini CLI",
  "version": "0.1.0",
  "author": {
    "name": "Mike Swift"
  },
  "license": "UNLICENSED",
  "keywords": [
    "personal",
    "ghostwriting",
    "skills",
    "workflows"
  ]
}
```

- [ ] **Step 2: Verify plugin structure is recognized**

Run: `ls -la .claude-plugin/plugin.json`
Expected: File exists with valid JSON.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: add Claude Code plugin manifest"
```

---

### Task 2: Cross-Platform Configuration (AGENTS.md + CLAUDE.md symlink)

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md` (symlink to AGENTS.md)

- [ ] **Step 1: Create AGENTS.md**

```markdown
# MechaSwift

Personal agent framework for Mike Swift. Skills, configuration, and workflows for working with coding agents.

## Identity

You are assisting Mike Swift, CEO & Co-Founder of Major League Hacking (MLH) and leader of DEV (dev.to). Mike works across software engineering, communications, and administrative tasks.

## Conventions

- Follow existing patterns in whatever project you're working in
- Prefer simple, direct solutions over clever ones
- When writing content as Mike, use the ghostwriting skill (Claude Code) or follow the voice profile in `skills/ghostwriting/references/voice-profile.md`

## Skills

Skills are located in the `skills/` directory. Each skill has a `SKILL.md` with activation triggers and instructions.

### Available Skills

- **ghostwriting** — Rewrite or draft content in Mike Swift's voice. See `skills/ghostwriting/SKILL.md`.
```

- [ ] **Step 2: Create CLAUDE.md as a symlink to AGENTS.md**

Run: `ln -s AGENTS.md CLAUDE.md`

- [ ] **Step 3: Verify the symlink**

Run: `ls -la CLAUDE.md`
Expected: `CLAUDE.md -> AGENTS.md`

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "feat: add AGENTS.md config and CLAUDE.md symlink"
```

---

### Task 3: Voice Profile Reference File

**Files:**
- Create: `skills/ghostwriting/references/voice-profile.md`

- [ ] **Step 1: Create the voice profile**

This file contains Mike's bio, style guide, values, and platform-specific formatting rules. It is loaded on-demand by the ghostwriting skill via backtick reference.

```markdown
# Mike Swift — Voice Profile

## Biography

Mike Swift is the CEO & Co-Founder of Major League Hacking (MLH), with a mission to create the home for the next billion software creators. MLH empowers technologists through hands-on programs (hackathons, internships, open source) that build practical skills and career pathways. MLH has acquired DEV (dev.to), the largest developer content network in the world.

- **Community Impact**: Between MLH & DEV, Swift's audience includes 10% of the world's software engineers annually. MLH's community reach includes 1 in 3 Computer Science students each year. DEV reaches 10 million unique developers per month.
- **Expertise**: Software engineering and building/scaling diverse, inclusive developer communities.
- **Recognition**: Forbes 30 Under 30 (Education).
- **Previous Ventures**: Founded Hacker League (acquired by Intel in 2013).
- **Career History**: First Developer Evangelist at SendGrid.
- **Current Roles**: Investment Partner at Flybridge's Next Wave NYC Fund.
- **Education**: Rutgers University, Computer Science.
- **Alias**: Also known as "Swift".

## Style Guide

### Tone
Energetic, encouraging, optimistic. Lead with possibility and momentum. Confident but humble.

### Voice
- Use community-first "we/our" when representing MLH or a team
- Use "I" for personal reflections or gratitude
- Address readers directly as "you"

### Purpose
Drive action that helps early-career developers learn by doing and ship something real.

### Values
Loyalty, high standards, humility, always-be-learning, learn-by-doing, elevate others, bias to action, enjoy the struggle.

### Diction
Plain, friendly, concrete. Use short active sentences. Minimal jargon; if used, explain it immediately.

### Framing
Start with a relatable hook or clear "why now". Move quickly to what to do next.

### Credibility
Cite concrete tools, models, sponsors, and resources. Keep claims specific and verifiable.

### Humor
Light, occasional, never at someone's expense. Pop-culture asides in parentheses are acceptable.

### Enthusiasm
Use upbeat verbs (build, ship, learn) and occasional exclamations without hype.

### Safety & Standards
Be transparent and direct on sensitive topics. Prioritize community safety and professionalism. State policies and next steps plainly.

### Consistency
Use American English. Maintain a friendly, helpful, high-integrity tone. Emphasize community and outcomes over ego.

## Formatting Preferences

- Use short paragraphs
- Use tight bullets
- Bold key actions and terms

## Phrases to Avoid

- Corporate buzzwords
- Vague impact claims
- Exclusionary tone
- Unexplained heavy jargon

## Platform-Specific Rules

### LinkedIn
Does not support rich text. Use emojis and line breaks to drive emphasis.

### Email
Keep subject lines short and action-oriented. Lead with the key ask or update in the first sentence.

### Blog Posts (DEV)
Use headers to break up sections. Include a clear call-to-action at the end.

### Slack / Chat
Keep messages concise. Use threads for longer context. Lead with the point.
```

- [ ] **Step 2: Commit**

```bash
git add skills/ghostwriting/references/voice-profile.md
git commit -m "feat: add Mike Swift voice profile reference file"
```

---

### Task 4: Ghostwriting Skill Definition

**Files:**
- Create: `skills/ghostwriting/SKILL.md`

**Note:** This task will use the `skill-creator` skill to build the SKILL.md, ensuring it follows best practices for activation rates and structure. The content below is the specification to provide to the skill-creator — the final SKILL.md may differ based on skill-creator guidance.

- [ ] **Step 1: Invoke the `skill-creator` skill**

Provide the skill-creator with this specification:

- **Skill name:** `ghostwriting`
- **Skill location:** `skills/ghostwriting/SKILL.md`
- **Description (for activation):** "Use when drafting, rewriting, or editing content as Mike Swift — emails, social posts, blog articles, announcements, messages."
- **Reference file:** `references/voice-profile.md` (loaded on-demand via backtick reference)
- **Hard constraints:**
  - No external information — do not search the web, pull training data, or invent context
  - Work only with content and context explicitly provided by the user
  - Do not generate content without user-supplied input
- **Behavior:**
  1. Accept user input (rough draft, bullet points, key messages, or a description)
  2. Determine content type and target platform from context or ask
  3. Load the voice profile reference
  4. Produce content matching Mike's voice, formatted for the target platform
  5. Present the result for user review and revision

- [ ] **Step 2: Review the generated SKILL.md**

Read `skills/ghostwriting/SKILL.md` and verify:
- Frontmatter has `name: ghostwriting` and a clear description
- Hard constraints (no external info, user-provided input only) are present
- Voice profile is referenced via backtick path, not embedded
- No placeholders or TODOs

- [ ] **Step 3: Commit**

```bash
git add skills/ghostwriting/SKILL.md
git commit -m "feat: add ghostwriting skill definition"
```

---

### Task 5: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Review current .gitignore**

Current contents:
```
.DS_Store
node_modules/
examples/
```

- [ ] **Step 2: Add plugin cache and OS artifacts**

Update `.gitignore` to:
```
.DS_Store
node_modules/
examples/
```

No changes needed — the current `.gitignore` already covers the necessary patterns. The `examples/` exclusion keeps the research reference material out of the plugin distribution.

- [ ] **Step 3: Skip commit (no changes)**

No changes to `.gitignore` are required.

---

### Task 6: Verify Plugin End-to-End

- [ ] **Step 1: Verify complete file structure**

Run: `find . -not -path './.git/*' -not -path './examples/*' -not -path './docs/*' | sort`

Expected output:
```
.
./.claude-plugin
./.claude-plugin/plugin.json
./.gitignore
./AGENTS.md
./CLAUDE.md
./skills
./skills/ghostwriting
./skills/ghostwriting/SKILL.md
./skills/ghostwriting/references
./skills/ghostwriting/references/voice-profile.md
```

- [ ] **Step 2: Verify CLAUDE.md symlink is valid**

Run: `cat CLAUDE.md | head -1`
Expected: `# MechaSwift`

- [ ] **Step 3: Verify plugin.json is valid JSON**

Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); print('Valid JSON')"`
Expected: `Valid JSON`

- [ ] **Step 4: Verify skill frontmatter**

Run: `head -5 skills/ghostwriting/SKILL.md`
Expected: YAML frontmatter with `name: ghostwriting` and a description field.

- [ ] **Step 5: Final commit if any loose changes**

```bash
git status
```

If clean, no commit needed. If changes exist, stage and commit with an appropriate message.
