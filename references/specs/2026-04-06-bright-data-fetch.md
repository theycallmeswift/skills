# Bright Data Web Fetch

**Date:** 2026-04-06
**Status:** Approved, ready for implementation plan

## Goal

Replace Claude Code's built-in `WebFetch` and `WebSearch` tools in MechaSwift with the Bright Data hosted MCP server. The agent and all skills get raw, unprocessed page content (no lossy small-model summarization) and real Google search results, sourced through a single MCP server.

## Why

Claude Code's `WebFetch` runs fetched content through an intermediate small model that summarizes before the result reaches the main agent. The tool description is explicit: *"Processes the content with the prompt using a small, fast model."* For some workflows (notably the `summarize` skill) this is lossy and degrades output. We want raw markdown straight to the agent.

Bright Data's hosted MCP server returns clean markdown via `scrape_as_markdown`, handles JS-rendered pages and most anti-bot blocks server-side, and includes a real `search_engine` tool. The free tier covers 5,000 requests per month, which is comfortably above personal-use volume.

## Architecture

One new MCP server, registered at the project level via `.mcp.json` using the hosted SSE endpoint at `https://mcp.brightdata.com/sse`. The API token is passed as a query parameter, sourced from the `BRIGHTDATA_API_TOKEN` environment variable using Claude Code's `${VAR}` substitution.

The five free-tier tools are all enabled:

- `scrape_as_markdown(url)`: fetch a single URL, return markdown
- `scrape_batch(urls)`: fetch multiple URLs in one call
- `search_engine(query)`: Google search with structured SERP results
- `search_engine_batch(queries)`: multiple searches in one call
- `discover(query)`: AI-ranked search with intent matching

`PRO_MODE` stays off. The 60+ specialized scrapers (LinkedIn, Amazon, Maps, etc.) are out of scope.

Built-in `WebFetch` and `WebSearch` are denied at the harness level via `.claude/settings.json` so the agent cannot fall back to them. This is enforced globally, not just inside any one skill.

## Components

| File | Status | Purpose |
|---|---|---|
| `.mcp.json` | new | Registers the brightdata SSE MCP server |
| `.env.example` | new | Documents required env vars |
| `.env` | new, gitignored | Placeholder, kept for future Claude Desktop native loading |
| `.gitignore` | edit | Add `.env`, document `.claude/settings.json` is tracked, ignore `.claude/settings.local.json` |
| `.claude/settings.json` | new | Deny `WebFetch` and `WebSearch` |
| `skills/summarize/SKILL.md` | edit | Use `scrape_as_markdown` or `scrape_batch` exclusively |
| `AGENTS.md` | edit | New "Web Access" section pointing skills at the brightdata MCP |
| `README.md` | edit | Short "Environment" subsection naming the required env var |

`CLAUDE.md` is a symlink to `AGENTS.md`, so editing `AGENTS.md` covers both.

## File specifications

### `.mcp.json`

```json
{
  "mcpServers": {
    "brightdata": {
      "type": "sse",
      "url": "https://mcp.brightdata.com/sse?token=${BRIGHTDATA_API_TOKEN}"
    }
  }
}
```

Claude Code expands `${BRIGHTDATA_API_TOKEN}` from the process environment when it loads the MCP config. If the variable is unset, Claude Code fails to parse the config and the brightdata server is unavailable.

### `.env.example`

```
# Bright Data hosted MCP server
# Get a token at https://brightdata.com/
BRIGHTDATA_API_TOKEN=
```

### `.env`

Empty placeholder file, gitignored. Kept in the working tree so the project's intent is visible and the file is ready for the day Claude Desktop natively loads `.env` files. For now, the actual env var is sourced from the user's shell profile, not this file.

### `.gitignore`

Append to the existing file:

```
# Secrets
.env

# Track .claude/ project config; ignore user-local overrides
.claude/settings.local.json
```

The comment is intentional. `.claude/settings.json` is part of the project and must be committed. Only the user-local override file is ignored.

### `.claude/settings.json`

```json
{
  "permissions": {
    "deny": ["WebFetch", "WebSearch"]
  }
}
```

This blocks the built-in tools at the harness level. The agent cannot invoke them at all. The five Bright Data tools remain available because they live under the `mcp__brightdata__*` namespace and are not denied.

### `skills/summarize/SKILL.md`

The "Getting the Content" section currently implies WebFetch for URLs. Update step 1 of the numbered Steps list to read:

> 1. **Fetch and read** the content. For a single URL, use `scrape_as_markdown` from the brightdata MCP. For multiple URLs in one request, use `scrape_batch`. For local files (PDFs, DOCX, etc.), use Read directly.

No fallback to WebFetch. If the brightdata MCP is unavailable, the skill should fail loudly with a message pointing the user at `BRIGHTDATA_API_TOKEN`.

### `AGENTS.md`

Add a new top-level section near the existing "Conventions" section:

> ## Web Access
>
> All web content goes through the `brightdata` MCP server. The built-in `WebFetch` and `WebSearch` tools are disabled at the harness level.
>
> - `scrape_as_markdown(url)`: fetch a single URL as clean markdown
> - `scrape_batch(urls)`: fetch multiple URLs in one call
> - `search_engine(query)`: Google search with structured results
> - `search_engine_batch(queries)`: multiple searches in one call
> - `discover(query)`: AI-ranked search with intent matching

### `README.md`

Add an "Environment" subsection under the existing "Install" section:

> ## Environment
>
> Set `BRIGHTDATA_API_TOKEN` in your environment. Get a token at [brightdata.com](https://brightdata.com/). Without it, the `brightdata` MCP server fails to load and skills that need web access will not work.

## Validation

After implementation:

1. `claude mcp list` shows `brightdata` connected via SSE
2. Attempting to invoke `WebFetch` or `WebSearch` directly returns a permission denial
3. Running `summarize` on a JS-heavy URL (e.g. a recent dev.to post or X thread) returns full content, not a stub
4. Running `summarize` on a previously-blocked URL works
5. `git status` confirms `.env` is not tracked
6. `git ls-files .claude/` confirms `.claude/settings.json` is tracked

## Out of scope

- `PRO_MODE` and the 60+ specialized scrapers
- Caching layer (Bright Data handles its own)
- Self-hosted Bright Data deployment
- Fallback fetch backends (Jina, Firecrawl, npx local server)
- Updating any other skill beyond `summarize`
- Tooling to verify the env var is set before Claude Code launches

## Known risks

- **Plugin loading bug.** Claude Code has an open issue where adding `WebFetch` or `WebSearch` to `permissions.deny` can break plugin loading in some configurations. This repo does not currently use plugins, so the risk is low. If it surfaces, fall back to enforcement via `AGENTS.md` instructions only and remove the deny rules.
- **Hard cutover.** If the Bright Data token is missing or the service has an outage, the agent has zero web access. This was an explicit design choice: no silent fallback to lossy WebFetch. The failure mode is loud.
- **Five tools instead of two.** The hosted SSE endpoint exposes all five free-tier tools and does not support server-side filtering. We accept the small overlap between `search_engine` and `discover` rather than denying tools at the harness layer.
