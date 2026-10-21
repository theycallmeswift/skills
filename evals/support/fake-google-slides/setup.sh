#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts, identically on both arms. See README.md.
FAKE_GOOGLE_SLIDES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAKE_GOOGLE_SLIDES_STATE=/workspace/.fake-google-slides

# add_google_slides [<meta-overlay.json>]: registers the fake as the guest's `Google_Slides` and
# `Google_Drive` MCP servers over a fresh copy of the deck. The overlay's fields replace the
# recorded `get_file_metadata` ones (an owner, say).
add_google_slides() {
  if ! command -v python3 >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
  fi
  mkdir -p "$FAKE_GOOGLE_SLIDES_STATE"
  cp "$FAKE_GOOGLE_SLIDES/deck.json" "$FAKE_GOOGLE_SLIDES_STATE/deck.json"
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fileContent"], end="")' \
    "$FAKE_GOOGLE_SLIDES/deck.txt" >"$FAKE_GOOGLE_SLIDES_STATE/deck.txt"
  if [ -n "${1:-}" ]; then
    cp "$1" "$FAKE_GOOGLE_SLIDES_STATE/meta-overlay.json"
  fi
  local server
  for server in Google_Slides Google_Drive; do
    HOME=/root /root/.local/bin/claude mcp add --scope user "$server" -- \
      python3 "$FAKE_GOOGLE_SLIDES/server.py" "$server" "$FAKE_GOOGLE_SLIDES_STATE" >/dev/null
  done
}

# add_google_workspace_skill: installs the stand-in `google-workspace` skill as a user skill.
add_google_workspace_skill() {
  mkdir -p /root/.claude/skills
  cp -R "$FAKE_GOOGLE_SLIDES/google-workspace" /root/.claude/skills/google-workspace
}
