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

pr_number=48
pr_title="Add idempotency keys to POST /payments"
pr_branch="feat/payment-idempotency"
pr_url="https://github.com/example/orders-api/pull/48"
run_url="https://github.com/example/orders-api/actions/runs/9051732"
pr_json="{\"number\":$pr_number,\"title\":\"$pr_title\",\"url\":\"$pr_url\",\"headRefName\":\"$pr_branch\",\"state\":\"OPEN\",\"isDraft\":false,\"statusCheckRollup\":[{\"name\":\"ty\",\"status\":\"COMPLETED\",\"conclusion\":\"FAILURE\",\"detailsUrl\":\"$run_url\"}]}"

wants_json() {
  for argument in "$@"; do
    if [ "$argument" = "--json" ] || [[ "$argument" = --json=* ]]; then
      return 0
    fi
  done
  return 1
}

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
  if wants_json "$@"; then
    printf '%s\n' "$pr_json"
    exit 0
  fi

  cat <<OUTPUT
title:  $pr_title
state:  OPEN
number: $pr_number
branch: $pr_branch
url:    $pr_url
checks: ty — failure
OUTPUT
  exit 0
fi

if [ "${1:-}" = "pr" ] && [ "${2:-}" = "status" ]; then
  if wants_json "$@"; then
    printf '{"currentBranch":%s,"createdBy":[%s],"needsReview":[]}\n' "$pr_json" "$pr_json"
    exit 0
  fi

  cat <<OUTPUT

Relevant pull requests in example/orders-api

Current branch
  #$pr_number  $pr_title [$pr_branch]
  - Checks failing

Created by you
  #$pr_number  $pr_title [$pr_branch]
  - Checks failing

Requesting a code review from you
  You have no pull requests to review

OUTPUT
  exit 0
fi

if [ "${1:-}" = "pr" ] && [ "${2:-}" = "list" ]; then
  if wants_json "$@"; then
    printf '[%s]\n' "$pr_json"
    exit 0
  fi

  printf '%s\t%s\t%s\tOPEN\n' "$pr_number" "$pr_title" "$pr_branch"
  exit 0
fi

if [ "${1:-}" = "pr" ] && [ "${2:-}" = "checks" ]; then
  printf 'ty\tfail\t12s\t%s\n' "$run_url"
  # Real gh exits 8 when any check is failing.
  exit 8
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
