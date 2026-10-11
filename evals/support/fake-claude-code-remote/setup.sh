#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts, identically on both arms. See README.md.
FAKE_CLAUDE_CODE_REMOTE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# add_routines <routines.json>: registers the fake as the guest's `claude_code_remote` MCP server.
add_routines() {
  local routines
  routines="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  if ! command -v python3 >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
  fi
  HOME=/root /root/.local/bin/claude mcp add --scope user claude_code_remote -- \
    python3 "$FAKE_CLAUDE_CODE_REMOTE/server.py" "$routines" \
    /workspace/.fake-claude-code-remote/calls.log >/dev/null
}
