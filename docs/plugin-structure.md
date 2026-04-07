# Plugin Structure

MechaSwift is a Claude Code **plugin**, not standalone `.claude/` configuration. The plugin manifest lives at `.claude-plugin/plugin.json`. Every other plugin component lives at the repo root.

Read this before touching skills, agents, commands, hooks, or MCP config. It exists because it is easy to forget that this repo is a plugin and reach for `.claude/`-style patterns that do not apply here.

## Why this matters

- Skills, agents, and commands are **namespaced** by the plugin name. They are invoked as `mechaswift:scope`, `mechaswift:summarize`, `mechaswift:researcher`, etc. Never invoke unprefixed.
- Subagents defined in `agents/` are loaded by the harness and called via the `Agent` tool with `subagent_type: "mechaswift:<name>"`. There is no need to copy/paste prompt content into a generic `general-purpose` agent — define a real subagent and reference it by type.
- The harness auto-loads anything in the canonical locations below. **Nothing except `plugin.json` belongs inside `.claude-plugin/`.** Putting `skills/`, `agents/`, `commands/`, or `hooks/` inside `.claude-plugin/` is the most common plugin mistake.

## Canonical layout

| Component   | Location                          | Notes |
|-------------|-----------------------------------|-------|
| Manifest    | `.claude-plugin/plugin.json`      | Only file in this directory |
| Skills      | `skills/<name>/SKILL.md`          | Optional `references/`, `evals/` alongside |
| Agents      | `agents/<name>.md`                | YAML frontmatter: `name`, `description`, `tools` |
| Commands    | `commands/<name>.md`              | Slash commands, namespaced as `/mechaswift:<name>` |
| Hooks       | `hooks/hooks.json`                | Not in `settings.json` |
| MCP servers | `.mcp.json`                       | Plugin root |
| Settings    | `settings.json`                   | Plugin defaults applied when enabled |

## Adding a subagent

Drop `agents/<name>.md` at the plugin root with frontmatter declaring the subagent's name, description, and allowed tools. The harness picks it up on load (or `/reload-plugins`). It then becomes available as `subagent_type: "mechaswift:<name>"` via the `Agent` tool. Skills that delegate work should reference the subagent by type, not by inlining its prompt.

## Local testing

```
claude --plugin-dir .
```

Then `/reload-plugins` after each change to pick up edits without restarting.

## Source

Upstream docs: https://code.claude.com/docs/en/plugins
