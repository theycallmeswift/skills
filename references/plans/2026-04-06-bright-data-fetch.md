# Bright Data Web Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Claude Code's built-in `WebFetch` and `WebSearch` with the Bright Data hosted MCP server, so the agent gets raw markdown and real Google SERPs through one server.

**Architecture:** Register the hosted Bright Data SSE endpoint (`https://mcp.brightdata.com/sse`) at the project level via `.mcp.json`, with the API token sourced from `BRIGHTDATA_API_TOKEN` using `${VAR}` substitution. Deny the built-in `WebFetch` and `WebSearch` tools at the harness level via `.claude/settings.json`. Update the `summarize` skill, `AGENTS.md`, and `README.md` to point everything at the new tools.

**Tech Stack:** Bright Data hosted MCP (SSE), Claude Code project-level MCP config (`.mcp.json`), Claude Code permission system (`.claude/settings.json`), `.env` / `.env.example` convention.

---

## File Structure

```
mechaswift/
├── .mcp.json                    # NEW: registers brightdata SSE MCP server
├── .env.example                 # NEW: documents BRIGHTDATA_API_TOKEN
├── .env                         # NEW (gitignored): empty placeholder
├── .gitignore                   # EDIT: add .env, .claude/settings.local.json
├── .claude/
│   └── settings.json            # NEW: denies WebFetch & WebSearch
├── skills/summarize/SKILL.md    # EDIT: point step 1 at brightdata MCP
├── AGENTS.md                    # EDIT: add "Web Access" section
└── README.md                    # EDIT: add "Environment" subsection
```

`CLAUDE.md` is a symlink to `AGENTS.md`, so editing `AGENTS.md` covers both.

This plan is mostly config and documentation edits. No test suite exists for these files, so each task uses a **make change, verify with an explicit command, commit** pattern instead of TDD red-green. Verification commands have expected output in every step.

---

### Task 1: Update `.gitignore` for `.env` and local settings

**Files:**
- Modify: `.gitignore`

The existing `.gitignore` has 6 lines and does not ignore `.env` or `.claude/settings.local.json`. We add both. `.claude/settings.local.json` is currently untracked (verified via `git ls-files .claude/`) so no `git rm --cached` is needed.

- [ ] **Step 1: Read the current `.gitignore`**

Run: `cat .gitignore`
Expected output:
```
.DS_Store
node_modules/
examples/
tmp/*
!tmp/.gitkeep
*-workspace/
```

- [ ] **Step 2: Append the new ignore rules**

Append these lines to `.gitignore`:

```
# Secrets
.env

# Track .claude/ project config; ignore user-local overrides
.claude/settings.local.json
```

The comment is intentional. `.claude/settings.json` (created in Task 3) IS tracked. Only the `.local.json` override is ignored.

- [ ] **Step 3: Verify `.gitignore` parses correctly**

Run: `git check-ignore -v .env .claude/settings.local.json`
Expected: both files print with the matching `.gitignore` rule. Exit code 0.

Run: `git check-ignore -v .claude/settings.json` (file does not yet exist, but the check works against the path)
Expected: exit code 1, no output. (Confirms `settings.json` is NOT ignored.)

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore .env and .claude/settings.local.json"
```

---

### Task 2: Create `.env.example` and empty `.env`

**Files:**
- Create: `.env.example`
- Create: `.env`

`.env.example` documents the required env var. `.env` is an empty placeholder kept in the working tree so the project's intent is visible (the file is gitignored, so the placeholder never reaches git).

- [ ] **Step 1: Create `.env.example`**

Write to `.env.example`:

```
# Bright Data hosted MCP server
# Get a token at https://brightdata.com/
BRIGHTDATA_API_TOKEN=
```

- [ ] **Step 2: Create empty `.env`**

Write an empty file to `.env` (no content, zero bytes is fine; one trailing newline is also fine).

- [ ] **Step 3: Verify `.env` is gitignored and `.env.example` is not**

Run: `git status --short`
Expected output should include `?? .env.example` but NOT `.env`. The `.env` line must be absent because `.gitignore` (from Task 1) excludes it.

Run: `git check-ignore -v .env`
Expected: prints the `.gitignore:N:.env` rule. Exit code 0.

- [ ] **Step 4: Commit `.env.example` only**

```bash
git add .env.example
git commit -m "chore: add .env.example for BRIGHTDATA_API_TOKEN"
```

Do NOT `git add .env`. It is gitignored and stays untracked locally.

---

### Task 3: Set the `BRIGHTDATA_API_TOKEN` environment variable

**Files:** none (shell profile edit, performed by the user)

This task is a one-time user action: get a Bright Data token and export it from the shell profile so Claude Code can substitute it into `.mcp.json`. The plan still tracks it as a checkbox so the executor knows to confirm it.

- [ ] **Step 1: Get a Bright Data API token**

Visit https://brightdata.com/, sign up for the free tier (5,000 req/month), and copy the API token from the dashboard.

- [ ] **Step 2: Export the token from the shell profile**

Add this line to `~/.zshrc` (or `~/.zprofile`, whichever loads on new shells):

```bash
export BRIGHTDATA_API_TOKEN="<paste-token-here>"
```

Then either restart the terminal or run:

```bash
source ~/.zshrc
```

- [ ] **Step 3: Verify the variable is set**

Run: `echo "${BRIGHTDATA_API_TOKEN:0:8}..."`
Expected: prints the first 8 characters of the token followed by `...`. If it prints `...` alone, the var is unset. Go back to Step 2.

- [ ] **Step 4: No commit**

This step touches no files in the repo. Skip the commit.

---

### Task 4: Register the brightdata MCP server in `.mcp.json`

**Files:**
- Create: `.mcp.json`

Project-level MCP config. Claude Code expands `${BRIGHTDATA_API_TOKEN}` from the process env when it loads this file.

- [ ] **Step 1: Create `.mcp.json`**

Write to `.mcp.json`:

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

- [ ] **Step 2: Verify the JSON parses**

Run: `python3 -c "import json; json.load(open('.mcp.json')); print('ok')"`
Expected output: `ok`

- [ ] **Step 3: Restart Claude Code so it loads the new MCP config**

Exit the current Claude Code session and start a fresh one in the same directory (`claude` from `/Users/theycallmeswift/dev/mechaswift`). MCP config is read at session start, so a restart is required for the new server to attach.

- [ ] **Step 4: Verify the brightdata server is connected**

Run: `claude mcp list`
Expected: output includes a line like `brightdata: https://mcp.brightdata.com/sse?token=... (SSE) - ✓ Connected`. If it shows `✗ Failed to connect`, re-check Task 3. The env var almost certainly is not exported in the shell that launched Claude Code.

- [ ] **Step 5: Verify the brightdata tools are available**

Inside the Claude Code session, ask: "List the brightdata MCP tools available to you."
Expected: the agent reports five tools: `scrape_as_markdown`, `scrape_batch`, `search_engine`, `search_engine_batch`, `discover` (each prefixed `mcp__brightdata__` in the actual tool namespace).

- [ ] **Step 6: Commit**

```bash
git add .mcp.json
git commit -m "feat: register brightdata SSE MCP server"
```

---

### Task 5: Deny built-in `WebFetch` and `WebSearch` at the harness level

**Files:**
- Create: `.claude/settings.json`

This blocks the built-in tools so the agent cannot fall back to them. The five Bright Data tools live under `mcp__brightdata__*` and remain available.

- [ ] **Step 1: Confirm `.claude/` exists**

Run: `ls -la .claude/`
Expected: directory exists, contains `settings.local.json` (untracked, gitignored by Task 1). If `.claude/` does not exist, create it: `mkdir -p .claude`.

- [ ] **Step 2: Create `.claude/settings.json`**

Write to `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": ["WebFetch", "WebSearch"]
  }
}
```

- [ ] **Step 3: Verify the JSON parses**

Run: `python3 -c "import json; json.load(open('.claude/settings.json')); print('ok')"`
Expected output: `ok`

- [ ] **Step 4: Verify `.claude/settings.json` is NOT gitignored**

Run: `git check-ignore -v .claude/settings.json`
Expected: exit code 1, no output (the file is tracked-eligible).

Run: `git status --short`
Expected: output includes `?? .claude/settings.json` but NOT `?? .claude/settings.local.json`.

- [ ] **Step 5: Restart Claude Code so it picks up the new deny rules**

Exit and relaunch the Claude Code session.

- [ ] **Step 6: Verify the deny rules are active**

Inside the new session, ask the agent to "fetch https://example.com using WebFetch directly, do not use any MCP tool."
Expected: the agent reports a permission denial for `WebFetch`. The exact wording varies but it must NOT successfully return page content via the built-in tool.

Then ask: "search Google for 'bright data mcp' using WebSearch directly."
Expected: same result, permission denial for `WebSearch`.

- [ ] **Step 7: Commit**

```bash
git add .claude/settings.json
git commit -m "feat: deny built-in WebFetch and WebSearch tools"
```

---

### Task 6: Update `skills/summarize/SKILL.md` to use brightdata exclusively

**Files:**
- Modify: `skills/summarize/SKILL.md` (the "Steps" section, step 1)

The current step 1 reads `1. **Fetch and read** the content`. Replace it with explicit instructions to use `scrape_as_markdown` / `scrape_batch` from the brightdata MCP, and add a loud-failure note.

- [ ] **Step 1: Read the current step 1 wording**

Run: `sed -n '20,23p' skills/summarize/SKILL.md`
Expected: shows `## Steps` heading and the line `1. **Fetch and read** the content`.

- [ ] **Step 2: Replace step 1 with the brightdata-explicit version**

Use Edit to replace this exact line in `skills/summarize/SKILL.md`:

Old:
```
1. **Fetch and read** the content
```

New:
```
1. **Fetch and read** the content. For a single URL, use `scrape_as_markdown` from the brightdata MCP. For multiple URLs in one request, use `scrape_batch`. For local files (PDFs, DOCX, etc.), use Read directly. If the brightdata MCP is unavailable, fail loudly with a message pointing the user at `BRIGHTDATA_API_TOKEN`. Do not fall back to any other fetch tool.
```

- [ ] **Step 3: Verify the edit landed**

Run: `grep -n "scrape_as_markdown" skills/summarize/SKILL.md`
Expected: one match on the step 1 line.

Run: `grep -n "WebFetch\|WebSearch" skills/summarize/SKILL.md`
Expected: zero matches. The skill must not reference the denied built-in tools.

- [ ] **Step 4: Commit**

```bash
git add skills/summarize/SKILL.md
git commit -m "feat(summarize): use brightdata MCP for web fetches"
```

---

### Task 7: Add a "Web Access" section to `AGENTS.md`

**Files:**
- Modify: `AGENTS.md`

`CLAUDE.md` is a symlink to `AGENTS.md`, so this single edit covers both. Insert the new section between `## Conventions` (ends at line 26) and `## Project Structure` (starts at line 28).

- [ ] **Step 1: Read the current section boundary**

Run: `sed -n '20,30p' AGENTS.md`
Expected: shows the tail of the Conventions list, a blank line, then `## Project Structure`.

- [ ] **Step 2: Insert the "Web Access" section after Conventions**

Use Edit to replace this exact block in `AGENTS.md`:

Old:
```
- Never cosign output as any specific AI model or tool. Don't reveal which harness or model is being used.

## Project Structure
```

New:
```
- Never cosign output as any specific AI model or tool. Don't reveal which harness or model is being used.

## Web Access

All web content goes through the `brightdata` MCP server. The built-in `WebFetch` and `WebSearch` tools are disabled at the harness level.

- `scrape_as_markdown(url)`: fetch a single URL as clean markdown
- `scrape_batch(urls)`: fetch multiple URLs in one call
- `search_engine(query)`: Google search with structured results
- `search_engine_batch(queries)`: multiple searches in one call
- `discover(query)`: AI-ranked search with intent matching

## Project Structure
```

- [ ] **Step 3: Verify the section landed and CLAUDE.md sees it through the symlink**

Run: `grep -n "## Web Access" AGENTS.md CLAUDE.md`
Expected: both files report a match on the same line number. (CLAUDE.md is a symlink, so it must reflect the edit.)

Run: `grep -n "scrape_as_markdown\|scrape_batch\|search_engine\|discover" AGENTS.md`
Expected: five matches, one per tool.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add Web Access section pointing skills at brightdata MCP"
```

---

### Task 8: Add an "Environment" subsection to `README.md`

**Files:**
- Modify: `README.md`

Insert the new section between the existing `## Install` block (ends around line 20) and `## Project Structure` (starts at line 22).

- [ ] **Step 1: Read the current section boundary**

Run: `sed -n '18,24p' README.md`
Expected: shows the tail of the Install section, a blank line, then `## Project Structure`.

- [ ] **Step 2: Insert the "Environment" subsection after Install**

Use Edit to replace this exact block in `README.md`:

Old:
```
Skills are available in every Claude Code session after install. Invoke them by name (e.g. `/ghostwrite`, `/scope`, `/summarize`).

## Project Structure
```

New:
```
Skills are available in every Claude Code session after install. Invoke them by name (e.g. `/ghostwrite`, `/scope`, `/summarize`).

## Environment

Set `BRIGHTDATA_API_TOKEN` in your environment. Get a token at [brightdata.com](https://brightdata.com/). Without it, the `brightdata` MCP server fails to load and skills that need web access will not work.

## Project Structure
```

- [ ] **Step 3: Verify the section landed**

Run: `grep -n "## Environment" README.md`
Expected: one match.

Run: `grep -n "BRIGHTDATA_API_TOKEN" README.md`
Expected: one match in the new section.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document BRIGHTDATA_API_TOKEN env var in README"
```

---

### Task 9: End-to-end validation against the spec

**Files:** none (verification only)

Run all six validation checks from the spec back-to-back. This is the gate before declaring the work complete.

- [ ] **Step 1: `claude mcp list` shows brightdata connected**

Run: `claude mcp list`
Expected: line with `brightdata` and `✓ Connected` (or equivalent success indicator). Already verified in Task 4. Re-run here as a regression check after the later edits.

- [ ] **Step 2: Direct `WebFetch` invocation is denied**

Inside a Claude Code session, ask the agent to "fetch https://example.com using the WebFetch tool directly."
Expected: permission denial. The agent cannot return page content via WebFetch.

- [ ] **Step 3: Direct `WebSearch` invocation is denied**

Ask the agent to "use WebSearch to search for 'mcp protocol'."
Expected: permission denial.

- [ ] **Step 4: `summarize` works on a JS-heavy URL**

Ask the agent to "summarize https://dev.to" (or pick a recent dev.to post URL with JS-rendered content that historically gave WebFetch trouble).
Expected: the summarize skill returns the standard Title / TL;DR / Cliff Notes / Share / Comment output, with real content from the page (not a stub or error).

- [ ] **Step 5: `summarize` works on a previously-blocked URL**

Pick a URL that the built-in WebFetch was known to bounce off (e.g. an X / Twitter thread or LinkedIn post). Ask the agent to summarize it.
Expected: real content, not a "this site requires JavaScript" stub or a 403 error. If this fails, the issue is upstream at Bright Data, not in this implementation. Note it and move on, but do not roll back the plan.

- [ ] **Step 6: `git status` confirms `.env` is not tracked**

Run: `git status --short`
Expected: no line mentioning `.env` (only `.env.example` from Task 2 should already be committed at this point).

Run: `git ls-files | grep -E '^\.env$'`
Expected: no output. Exit code 1.

- [ ] **Step 7: `git ls-files .claude/` confirms `settings.json` is tracked**

Run: `git ls-files .claude/`
Expected output (exactly):
```
.claude/settings.json
```

`settings.local.json` MUST NOT appear in the output.

- [ ] **Step 8: No commit**

Validation only. Nothing to commit.

---

## Notes for the executor

- **Order matters for Tasks 3 → 4 → 5.** The env var must be set in the shell that launches Claude Code BEFORE `.mcp.json` is loaded, and the settings deny rules need a Claude Code restart to take effect. Do not skip the restarts in Task 4 Step 3 and Task 5 Step 5.
- **Plugin loading risk.** The spec flags an open Claude Code issue where adding `WebFetch` / `WebSearch` to `permissions.deny` can break plugin loading in some configurations. This repo does not currently use plugins, so the risk is low. If plugin loading breaks after Task 5, revert `.claude/settings.json` and rely on the AGENTS.md "Web Access" section to enforce the policy via instructions only.
- **Hard cutover, no fallback.** If the Bright Data token is missing or the service has an outage, the agent has zero web access. This is intentional. Do not add a silent fallback to WebFetch.
- **Out of scope** (do not implement, even if tempting): `PRO_MODE`, the 60+ specialized scrapers, a caching layer, self-hosted Bright Data, Jina/Firecrawl fallbacks, edits to any skill other than `summarize`, pre-launch token verification tooling.
