#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts. See README.md.

install_gh() {
  local install_dir="${FAKE_GH_INSTALL_DIR:-/usr/local/bin}"
  local fake_gh
  fake_gh="$(mktemp)"

  cat > "$fake_gh" <<'FAKE_GH'
#!/usr/bin/env bash
set -u

log_dir="${FAKE_GH_LOG_DIR:-/workspace/.fake-gh}"
mkdir -p "$log_dir"
{
  printf 'argv: gh'
  printf ' %q' "$@"
  printf '\n'
} >> "$log_dir/calls.log"

if [ "${1:-}" = "--version" ]; then
  printf 'gh version 2.80.0 (2026-09-10)\n'
  printf 'https://github.com/cli/cli/releases/tag/v2.80.0\n'
  exit 0
fi

if [ "${1:-}" = "auth" ] && [ "${2:-}" = "status" ]; then
  printf 'github.com\n'
  printf '  ✓ Logged in to github.com account eval-user\n'
  exit 0
fi

if [ "${1:-}" = "pr" ] && [ "${2:-}" = "view" ]; then
  for argument in "$@"; do
    if [ "$argument" = "--json" ] || [[ "$argument" = --json=* ]]; then
      printf '%s\n' '{"number":48,"state":"OPEN","statusCheckRollup":[{"name":"ty","status":"COMPLETED","conclusion":"FAILURE"}]}'
      exit 0
    fi
  done

  cat <<'OUTPUT'
title:  Add catch-me-up eval suite
state:  OPEN
number: 48
checks: ty — failure
OUTPUT
  exit 0
fi

if [ "${1:-}" = "pr" ] && [ "${2:-}" = "checks" ]; then
  printf 'ty\tfail\t12s\thttps://github.com/example/mechaswift/actions/runs/48\n'
  exit 1
fi

printf 'fake gh: unsupported command: gh' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 2
FAKE_GH

  mkdir -p "$install_dir"
  install -m 0755 "$fake_gh" "$install_dir/gh"
  rm -f "$fake_gh"

  if [ "$install_dir" != "/usr/local/bin" ]; then
    PATH="$install_dir:$PATH"
    export PATH
  fi
}
