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

cd /workspace
git init -q
printf '.fake-gh/\n' >> .git/info/exclude
git add api/payments.py api/models.py migrations/0014_idempotency.sql
git commit -qm "Initial eval fixtures"
git checkout -qb eval/stale-state

printf '\n\ndef hash_body(body):\n    raise NotImplementedError\n' >> api/payments.py
printf '\nALTER TABLE payment_idempotency ADD COLUMN expires_at TIMESTAMPTZ;\n' >> migrations/0014_idempotency.sql

expected_status=$' M api/payments.py\n M migrations/0014_idempotency.sql'
actual_status="$(git status --porcelain --untracked-files=no)"
if [ "$actual_status" != "$expected_status" ]; then
  printf 'unexpected stale-state fixture status:\n%s\n' "$actual_status" >&2
  exit 1
fi
