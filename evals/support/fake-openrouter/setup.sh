#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts, identically on both arms. See README.md.
FAKE_OPENROUTER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAKE_OPENROUTER_STATE=/workspace/.fake-openrouter
FAKE_OPENROUTER_HOME=/opt/fake-openrouter
FAKE_OPENROUTER_PORT="${FAKE_OPENROUTER_PORT:-8787}"
FAKE_OPENROUTER_URL="http://127.0.0.1:$FAKE_OPENROUTER_PORT/api/v1"

# add_fake_openrouter <scenario.json>: starts the fake as a detached daemon in the guest and makes
# every shell the agent opens see OPENROUTER_BASE_URL and OPENROUTER_API_KEY=sk-or-fake. The server
# and scenario are copied out of the project mount; calls land in /workspace/.fake-openrouter.
add_fake_openrouter() {
  local scenario="$1"
  if ! command -v python3 >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
  fi
  mkdir -p "$FAKE_OPENROUTER_STATE" "$FAKE_OPENROUTER_HOME"
  cp -R "$FAKE_OPENROUTER/server.py" "$FAKE_OPENROUTER/fixtures" "$FAKE_OPENROUTER_HOME/"
  cp "$scenario" "$FAKE_OPENROUTER_HOME/scenario.json"
  # The scenario's own folder may hold content files its replies name.
  cp -n "$(dirname "$scenario")"/*.json "$(dirname "$scenario")"/*.txt "$FAKE_OPENROUTER_HOME/" 2>/dev/null || true

  # setsid + nohup + closed fds: `docker exec` waits on the setup shell's pipes, so a daemon that
  # keeps them open would hang setup. The container's `sleep infinity` keeps the daemon alive.
  setsid nohup python3 "$FAKE_OPENROUTER_HOME/server.py" \
    --scenario "$FAKE_OPENROUTER_HOME/scenario.json" --state "$FAKE_OPENROUTER_STATE" \
    --port "$FAKE_OPENROUTER_PORT" >/dev/null 2>&1 </dev/null &
  local i
  for i in $(seq 1 50); do
    python3 - "$FAKE_OPENROUTER_URL/models" <<'PY' 2>/dev/null && break
import sys, urllib.request
urllib.request.urlopen(sys.argv[1], timeout=1).read()
PY
    sleep 0.1
  done
  if [ "$i" = 50 ]; then
    echo "fake-openrouter did not start on port $FAKE_OPENROUTER_PORT" >&2
    return 1
  fi
  : >"$FAKE_OPENROUTER_STATE/calls.log" # drop the readiness probes
  _fake_openrouter_export_env
}

# The agent turn is a fresh `docker exec` that never sees this shell's env, so the two variables
# are written everywhere a claude process or its Bash tool may read them (see README.md).
_fake_openrouter_export_env() {
  local url="$FAKE_OPENROUTER_URL" key=sk-or-fake
  mkdir -p /root/.claude
  python3 - "$url" "$key" <<'PY'
import json, os, sys
path = "/root/.claude/settings.json"
try:
    settings = json.load(open(path))
except (OSError, ValueError):
    settings = {}
settings.setdefault("env", {}).update(
    {"OPENROUTER_BASE_URL": sys.argv[1], "OPENROUTER_API_KEY": sys.argv[2]}
)
json.dump(settings, open(path, "w"), indent=2)
PY
  {
    echo "OPENROUTER_BASE_URL=$url"
    echo "OPENROUTER_API_KEY=$key"
  } >>/etc/environment
  printf 'export OPENROUTER_BASE_URL=%s\nexport OPENROUTER_API_KEY=%s\n' "$url" "$key" \
    >/etc/profile.d/fake-openrouter.sh
  printf '\nexport OPENROUTER_BASE_URL=%s\nexport OPENROUTER_API_KEY=%s\n' "$url" "$key" \
    >>/root/.bashrc
  printf 'OPENROUTER_BASE_URL=%s\nOPENROUTER_API_KEY=%s\n' "$url" "$key" >/workspace/.env
}
