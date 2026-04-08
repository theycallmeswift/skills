# `.claude/rules` Research

**Date:** 2026-04-07
**Sources:**
- Codebase: `~/dev/claude-code` (`src/utils/claudemd.ts`, `src/context.ts`, `src/tools/SkillTool/`)
- Official docs: https://code.claude.com/docs/en/memory

## What `.claude/rules` are

Markdown files in a `.claude/rules/` directory that give Claude persistent, modular instructions. Alternative to stuffing everything into one `CLAUDE.md`. Each file should cover one topic (e.g. `testing.md`, `api-design.md`). Discovered recursively, so subdirectories like `frontend/` or `backend/` are fine.

Rules without frontmatter load unconditionally at the same priority as `.claude/CLAUDE.md`. Rules with a `paths:` frontmatter field are **path-scoped** — only loaded when Claude reads a file matching the glob.

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/**/*.{ts,tsx}"
---

# API Development Rules
- All endpoints must include input validation
```

Symlinks are supported (including circular-symlink detection) — useful for sharing a rules set across projects:

```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

## Discovery tiers

| Tier | Location | Priority |
|---|---|---|
| Managed CLAUDE.md | macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`; Linux/WSL `/etc/claude-code/CLAUDE.md`; Windows `C:\Program Files\ClaudeCode\CLAUDE.md` | Lowest; **cannot** be excluded via `claudeMdExcludes` |
| User rules | `~/.claude/rules/*.md` | Loaded **before** project rules |
| Project rules | `./.claude/rules/**/*.md` | Highest — project rules win over user rules |

Project rules share priority with `./.claude/CLAUDE.md`. `CLAUDE.local.md` is appended after `CLAUDE.md` within each directory, so personal notes override at that level.

## When they load

**Delivery mechanism — important:** Rules and CLAUDE.md are **not** injected into the system prompt. They're delivered as a **user message after** the system prompt. Claude reads them and tries to comply, but there's no hard enforcement. For true system-prompt-level instructions use `--append-system-prompt`.

**Eager (session start):**
- Unconditional rules from managed, user, and project tiers
- Entry: `getUserContext()` → `getMemoryFiles()` → `getClaudeMds()`
  - `src/context.ts:155-189`
  - `src/utils/claudemd.ts:790-1075` (`getMemoryFiles`, memoized per session)
  - `src/utils/claudemd.ts:1147-1195` (`getClaudeMds` formats the addendum)
- Ancestor directories from root → CWD are walked; all discovered files are concatenated (not overridden)
- Block-level HTML comments (`<!-- ... -->`) are stripped before injection; comments inside code blocks are preserved

**Lazy (on demand):**
- Path-scoped rules (with `paths:` frontmatter) load when Claude **reads a matching file**, not on every tool use
- Also: nested `CLAUDE.md` / `CLAUDE.local.md` in subdirectories load when Claude touches files in those subdirs
- API: `getManagedAndUserConditionalRules(targetPath)` at `src/utils/claudemd.ts:1205-1238`
- Per-directory loader: `getMemoryFilesForNestedDirectory` at `src/utils/claudemd.ts:1249-1315`
- Matching: picomatch globs; base path is the project root for managed/user rules, or the dir containing `.claude` for project rules (`src/utils/claudemd.ts:1379-1380`)

**Compaction:** CLAUDE.md / rules fully survive `/compact` — re-read from disk and re-injected. Anything lost after compaction was only in conversation, never written to a rules file.

**Additional directories:** `.claude/rules/*.md` from `--add-dir` paths load **only** if `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` is set. `CLAUDE.local.md` is never loaded from additional dirs.

**Hook:** An `InstructionsLoaded` hook fires with `{ path, type, reason, metadata }` where `reason` is `session_start` | `compact` | `include`. Useful for debugging path-specific or lazy-loaded rules.

## Rules vs Skills

The docs draw the line cleanly:
- **Rules** — load every session (unconditional) or when matching files are opened (path-scoped)
- **Skills** — load only when invoked by the user or when Claude decides they're relevant to the prompt

| | `.claude/rules` | Skills |
|---|---|---|
| Nature | Passive text guidance | Active, invokable workflow |
| Load time | Eager (session start) + lazy (per matching file read) | On demand |
| Trigger | Automatic | Explicit `/name` or model-initiated `SkillTool` call |
| Delivered as | User message after system prompt | Loaded into the invoking turn / forked agent |
| Token cost | Paid every turn while loaded | Paid only when invoked |
| Execution | None — just instructions | Can fork an agent (`executeForkedSkill`, `src/tools/SkillTool/SkillTool.ts:122-130`) |
| Discovery | `.claude/rules/` at managed/user/project tiers | `~/.claude/skills/`, `.claude/skills/`, bundled (`src/skills/loadSkillsDir.ts`) |
| Compliance | Context, not enforced | Scoped prompt with its own instructions |

**Rule of thumb:** if it should be present by default (globally or per file glob), it's a rule. If it's a task-specific workflow that shouldn't burn context until needed, it's a skill.

## Key code locations

| Function | Path | Lines |
|---|---|---|
| `getUserContext` | `src/context.ts` | 155-189 |
| `getMemoryFiles` | `src/utils/claudemd.ts` | 790-1075 |
| `processMdRules` | `src/utils/claudemd.ts` | 697-788 |
| `processConditionedMdRules` | `src/utils/claudemd.ts` | 1345-1435 |
| `getManagedAndUserConditionalRules` | `src/utils/claudemd.ts` | 1205-1238 |
| `getMemoryFilesForNestedDirectory` | `src/utils/claudemd.ts` | 1249-1315 |
| `getClaudeMds` | `src/utils/claudemd.ts` | 1147-1195 |
| Symlink dedup | `src/utils/claudemd.ts` | 719-727 |
| `buildEffectiveSystemPrompt` | `src/utils/systemPrompt.ts` | 41-123 |
| `fetchSystemPromptParts` | `src/utils/queryContext.ts` | 44-74 |
| `SkillTool.executeForkedSkill` | `src/tools/SkillTool/SkillTool.ts` | 122-130 |

## Gotchas

- Rules are context, not config — vague or conflicting rules get partial compliance at best
- Managed CLAUDE.md is `/etc/claude-code/CLAUDE.md` (file), **not** `/etc/claude-code/.claude/rules/` (dir)
- User rules load before project rules → project rules win on conflict
- Path-scoped rules fire on file **reads**, not every tool call
- `claudeMdExcludes` (in `.claude/settings.local.json`) can skip noisy ancestor rules in monorepos, but cannot exclude managed policy
- Use `/memory` to see exactly which rules files are loaded in the current session
