# MechaSwift v1 — Project Plan

Mike Swift's personal framework for working with coding agents (Claude Code, Claude Cowork, Gemini CLI). Skills, configuration, and workflows that make agents more useful across software engineering, communications, and administrative work.

---

## Goals

- Ship a working Claude Code plugin with one immediately useful skill (ghostwrite)
- Maintain Gemini CLI compatibility via AGENTS.md
- Establish the project structure and conventions that future skills will follow
- Keep it simple — no speculative features, no over-engineering

## Architecture

### Plugin-first design

MechaSwift is a Claude Code plugin installed globally, making skills available in every session regardless of project. Cross-platform compatibility is handled via AGENTS.md (the universal standard adopted by the Linux Foundation).

### Project structure

```
mechaswift/
  .claude-plugin/
    plugin.json              # Plugin manifest (name, version, skills list)
  skills/
    ghostwrite/
      SKILL.md               # Skill definition and activation triggers
      references/
        voice-profile.md     # Bio, style guide, platform formatting rules
  AGENTS.md                  # Cross-platform config (source of truth)
  CLAUDE.md                  # Symlink to AGENTS.md
  docs/
    research/                # Existing research
    plans/                   # This file and future plans
```

### Key decisions

- **AGENTS.md is the source of truth.** CLAUDE.md is a symlink to it. If Claude-specific directives are ever needed, the symlink can be broken — but start unified.
- **Skills live in `skills/` at the repo root**, following standard plugin conventions.
- **Voice profile is a reference file**, not embedded in the skill definition. Keeps the skill lean and the profile reusable across future skills that need to write in Mike's voice.
- **No build step, no dependencies.** All markdown files and a JSON manifest. Clone, install, done.

## Ghostwriting Skill

### Purpose

A pure content rewriter that takes Mike's rough input and produces polished content in his voice, formatted for the target platform.

### Hard constraints

- **No external information.** The skill does not search the web, pull training data, or invent context. It works only with the content and context explicitly provided by the user.
- **User-provided input only.** It transforms, polishes, or drafts content based on what the user provides (rough drafts, bullet points, key messages). It does not generate content without user-supplied input or context.

### Activation

Triggers when the user asks to write, draft, rewrite, or edit content in Mike's voice. Skill description: "Use when drafting, rewriting, or editing content as Mike Swift — emails, social posts, blog articles, announcements, messages."

### How it works

1. Takes user input (rough draft, bullet points, or a description of what's needed)
2. Determines the content type and target platform (LinkedIn, email, DEV blog post, Slack, etc.)
3. Loads `references/voice-profile.md` for style guide, bio, and platform-specific formatting
4. Produces content matching Mike's voice, formatted appropriately for the platform

### Voice profile (`references/voice-profile.md`)

Contains:

- **Bio:** Mike Swift's background, roles, accomplishments, and areas of expertise
- **Style guide:** Tone (energetic, encouraging, optimistic), voice conventions (community-first "we/our" vs personal "I"), diction (plain, friendly, concrete, short active sentences), formatting preferences (short paragraphs, tight bullets, bold key terms)
- **Values:** Loyalty, high standards, humility, always-be-learning, learn-by-doing, elevate others, bias to action, enjoy the struggle
- **Platform-specific rules:** LinkedIn (no rich text — use emojis and line breaks), and others as added
- **Anti-patterns:** No corporate buzzwords, no vague impact claims, no exclusionary tone, no unexplained jargon

### Skill creation

The ghostwrite skill will be built using the `skill-creator` skill to ensure it follows best practices for activation rates, structure, and testing.

## Installation

### Claude Code

Install as a global plugin. Skills become available in every session regardless of project context.

### Gemini CLI

Reference `AGENTS.md` from Gemini CLI configuration. Skills don't auto-activate like in Claude Code — the behavioral guidance and style rules are picked up from AGENTS.md.

## Out of Scope (v1)

The following are intentionally excluded from v1. They represent natural growth areas informed by the research in `docs/research/agent-framework-best-practices.md`:

- Hooks (auto-formatting, quality gates, dangerous command blocking)
- Custom commands (slash commands beyond skill activation)
- Memory system (beyond Claude Code's native memory)
- Additional skills (debugging, research, admin workflows, TDD, code review)
- Multi-agent orchestration patterns (wave execution, parallel research)
- Error registry and lessons system
- Automated tests or evals for skills
- Multi-plugin or per-project installation modes
