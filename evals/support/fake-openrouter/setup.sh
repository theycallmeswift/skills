#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts, identically on both arms. See README.md.
FAKE_OPENROUTER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAKE_OPENROUTER_STATE=/workspace/.fake-openrouter
FAKE_OPENROUTER_HOME=/opt/fake-openrouter

# add_fake_openrouter <scenario.json>: starts the fake as a detached daemon in the guest and makes
# every shell the agent opens see OPENROUTER_BASE_URL and OPENROUTER_API_KEY=sk-or-fake. The server
# and scenario are copied out of the project mount; calls land in /workspace/.fake-openrouter.
add_fake_openrouter() {
  local scenario="$1"
  if ! command -v python3 >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
  fi
  # A free port, not a fixed one: a guest may share the host's network (Docker `--network host`),
  # so parallel cells would otherwise bind one port and log into each other's calls.log.
  FAKE_OPENROUTER_PORT="${FAKE_OPENROUTER_PORT:-$(python3 -c 'import socket
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])')}"
  FAKE_OPENROUTER_URL="http://127.0.0.1:$FAKE_OPENROUTER_PORT/api/v1"
  mkdir -p "$FAKE_OPENROUTER_STATE" "$FAKE_OPENROUTER_HOME"
  cp -R "$FAKE_OPENROUTER/server.py" "$FAKE_OPENROUTER/fixtures" "$FAKE_OPENROUTER_HOME/"
  cp "$scenario" "$FAKE_OPENROUTER_HOME/scenario.json"
  # The scenario's own folder may hold content files its replies name.
  cp -n "$(dirname "$scenario")"/*.json "$(dirname "$scenario")"/*.txt "$FAKE_OPENROUTER_HOME/" 2>/dev/null || true

  # An agent on OpenRouter (benchspec's openrouter provider hands it ANTHROPIC_AUTH_TOKEN) would
  # lose its model to the openrouter.ai block below, so the fake relays its Messages API calls,
  # and only those, through the egress proxy.
  local forward=()
  if [ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
    forward=(--forward-agent https://openrouter.ai/api)
  fi

  # setsid + nohup + closed fds: `docker exec` waits on the setup shell's pipes, so a daemon that
  # keeps them open would hang setup. The container's `sleep infinity` keeps the daemon alive.
  setsid nohup python3 "$FAKE_OPENROUTER_HOME/server.py" \
    --scenario "$FAKE_OPENROUTER_HOME/scenario.json" --state "$FAKE_OPENROUTER_STATE" \
    --port "$FAKE_OPENROUTER_PORT" "${forward[@]}" >/dev/null 2>&1 </dev/null &
  local pid=$! i
  for i in $(seq 1 50); do
    python3 - "$FAKE_OPENROUTER_URL/models" <<'PY' 2>/dev/null && break
import sys, urllib.request
urllib.request.urlopen(sys.argv[1], timeout=1).read()
PY
    sleep 0.1
  done
  # A dead pid means the port was taken and the probe answered someone else's fake.
  if [ "$i" = 50 ] || ! kill -0 "$pid" 2>/dev/null; then
    echo "fake-openrouter did not start on port $FAKE_OPENROUTER_PORT" >&2
    return 1
  fi
  : >"$FAKE_OPENROUTER_STATE/calls.log" # drop the readiness probes
  _fake_openrouter_export_env
}

# The agent turn is a fresh `docker exec` that never sees this shell's env, so the variables are
# written everywhere a claude process or its Bash tool may read them (see README.md). The real
# openrouter.ai is made unreachable too: a guest's egress proxy may attach a real key to any
# request for that host, so a script that misses the base URL would spend real money.
_fake_openrouter_export_env() {
  local url="$FAKE_OPENROUTER_URL" key=sk-or-fake agent_url=""
  local no_proxy="${NO_PROXY:-localhost,127.0.0.1},openrouter.ai"
  if [ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
    agent_url="http://127.0.0.1:$FAKE_OPENROUTER_PORT/agent"
  fi
  echo "127.0.0.1 openrouter.ai" >>/etc/hosts
  mkdir -p /root/.claude
  python3 - "$url" "$key" "$no_proxy" "$agent_url" <<'PY'
import json, os, sys
path = "/root/.claude/settings.json"
try:
    settings = json.load(open(path))
except (OSError, ValueError):
    settings = {}
settings.setdefault("env", {}).update(
    {
        "OPENROUTER_BASE_URL": sys.argv[1],
        "OPENROUTER_API_KEY": sys.argv[2],
        "NO_PROXY": sys.argv[3],
        "no_proxy": sys.argv[3],
    }
)
# Settings env overrides the exec env, so the agent's own model calls go to the relay.
if sys.argv[4]:
    settings["env"]["ANTHROPIC_BASE_URL"] = sys.argv[4]
json.dump(settings, open(path, "w"), indent=2)
PY
  {
    echo "OPENROUTER_BASE_URL=$url"
    echo "OPENROUTER_API_KEY=$key"
    echo "NO_PROXY=$no_proxy"
    echo "no_proxy=$no_proxy"
  } >>/etc/environment
  local exports
  exports="$(printf 'export OPENROUTER_BASE_URL=%s OPENROUTER_API_KEY=%s NO_PROXY=%s no_proxy=%s' \
    "$url" "$key" "$no_proxy" "$no_proxy")"
  echo "$exports" >/etc/profile.d/fake-openrouter.sh
  printf '\n%s\n' "$exports" >>/root/.bashrc
  printf 'OPENROUTER_BASE_URL=%s\nOPENROUTER_API_KEY=%s\n' "$url" "$key" >/workspace/.env
}
