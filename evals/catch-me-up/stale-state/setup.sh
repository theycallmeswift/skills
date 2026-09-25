#!/usr/bin/env bash
set -euo pipefail

source ../../support/fake-gh/setup.sh
install_gh

if ! command -v git >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git >/dev/null
fi

git config --global init.defaultBranch main
git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global --add safe.directory /workspace

branch="feat/payment-idempotency"
remote_url="https://github.com/example/orders-api.git"

cd /workspace
seed="$(mktemp -d)"
cp -R api migrations tests "$seed/"
rm -rf api migrations tests

# main: the endpoint as it was before the session, charging before any dedupe check.
git init -q
printf '.fake-gh/\n' >> .git/info/exclude
mkdir -p api
cat > api/payments.py <<'PY'
"""Payment submission endpoint."""


def create_payment(request, db):
    """Charge the card and record the payment."""
    return db.charge(request)
PY
git add api/payments.py
git commit -qm "Add POST /payments endpoint"

# The session's work, committed and pushed as the transcript says.
git checkout -qb "$branch"
mkdir -p migrations
cp "$seed/migrations/0014_idempotency.sql" migrations/
git add migrations/0014_idempotency.sql
git commit -qm "Add payment_idempotency table"
cp "$seed/api/models.py" api/
git add api/models.py
git commit -qm "Add IdempotencyRecord model"
cp "$seed/api/payments.py" api/
cp -R "$seed/tests" .
git add api/payments.py tests
git commit -qm "Dedupe POST /payments on Idempotency-Key"
rm -rf "$seed"

# Pushed without a network: write the remote-tracking refs the push would have left.
git remote add origin "$remote_url"
git update-ref refs/remotes/origin/main main
git update-ref "refs/remotes/origin/$branch" HEAD
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
git branch -q --set-upstream-to=origin/main main
git branch -q --set-upstream-to="origin/$branch" "$branch"

# The drift the transcript's closing turn does not know about.
printf '\n\ndef hash_body(body):\n    raise NotImplementedError\n' >> api/payments.py
printf '\n-- TODO: confirm the sweep job uses the expires_at index.\n' >> migrations/0014_idempotency.sql

fail() {
  printf 'unexpected stale-state fixture: %s\n' "$1" >&2
  exit 1
}

expected_status=$' M api/payments.py\n M migrations/0014_idempotency.sql'
actual_status="$(git status --porcelain)"
[ "$actual_status" = "$expected_status" ] || fail "status"$'\n'"$actual_status"
[ "$(git rev-parse --abbrev-ref HEAD)" = "$branch" ] || fail "branch"
[ "$(git rev-parse --abbrev-ref '@{u}')" = "origin/$branch" ] || fail "upstream"
[ "$(git rev-list --count main..HEAD)" = "3" ] || fail "commits ahead of main"
[ "$(git rev-list --count '@{u}'...HEAD)" = "0" ] || fail "branch differs from its upstream"
[ "$(git remote get-url origin)" = "$remote_url" ] || fail "remote url"
