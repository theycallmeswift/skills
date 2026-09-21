#!/usr/bin/env bash
set -euo pipefail

source ../../support/fake-gh/setup.sh
install_gh

git config --global init.defaultBranch main
git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global --add safe.directory /workspace

cd /workspace
git init -q
printf '.fake-gh/\n' >> .git/info/exclude
git add project-notes.md verification.md
git commit -qm "Initial eval fixtures"
git checkout -qb eval/stale-state

printf '\nThe stale-state fixture still needs local verification.\n' >> project-notes.md
printf '\n- Collection count re-checked after the latest fixture edits\n' >> verification.md

expected_status=$' M project-notes.md\n M verification.md'
actual_status="$(git status --porcelain --untracked-files=no)"
if [ "$actual_status" != "$expected_status" ]; then
  printf 'unexpected stale-state fixture status:\n%s\n' "$actual_status" >&2
  exit 1
fi
