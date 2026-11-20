#!/usr/bin/env bash
set -euo pipefail

# Provision the tools the gates call, identically on both arms. Network may be
# closed; a missing tool is then the agent's to report, not the fixture's.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null || true
apt-get install -y -qq git make curl ca-certificates nodejs npm >/dev/null || true
if ! command -v git >/dev/null; then
  printf 'unexpected monorepo-adoption fixture: no git\n' >&2
  exit 1
fi
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh >/dev/null 2>&1 || true
fi

git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global --add safe.directory '*'

# The judge reads every file under /workspace as text, and a small loose git
# object can decode as text with NUL bytes, so the git dir lives outside it.
gitdir="/srv/relay-workspace.git"

cd /workspace
git init -q --template= --separate-git-dir="$gitdir" -b main
git add package.json src test .gitignore
git commit -qm "Add digest worker"
git add pipeline
git commit -qm "Add nightly ingest pipeline"
git add prompts docs scripts
git commit -qm "Add summarize prompt, runbook and docs publishing"

# Git-ignored local state the pipeline's tests read: present on this machine,
# absent from any clean checkout. Written here because the repo's own
# .gitignore would keep it out of the eval fixture too.
mkdir -p pipeline/data
cat > pipeline/data/sources.json <<'JSON'
[
  {"name": "hn", "url": "https://news.ycombinator.com/rss"},
  {"name": "lobsters", "url": "https://lobste.rs/rss", "enabled": false}
]
JSON

fail() {
  printf 'unexpected monorepo-adoption fixture: %s\n' "$1" >&2
  exit 1
}

[ "$(git rev-list --count HEAD)" = 3 ] || fail "history"
[ -z "$(git status --porcelain)" ] || fail "dirty tree"
git check-ignore -q pipeline/data/sources.json || fail "sources.json not ignored"
