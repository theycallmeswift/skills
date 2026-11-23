#!/usr/bin/env bash
set -euo pipefail

# Provision uv for the Python gates, identically on both arms. Node stays out:
# the judge reads every file under /workspace into one prompt, and npm would
# fill it with node_modules. A missing tool is the agent's to report. The eval
# sets in pyproject.toml set UV_PROJECT_ENVIRONMENT, so uv's venv stays out of
# /workspace too.
export DEBIAN_FRONTEND=noninteractive
need=()
for tool in git make curl; do
  command -v "$tool" >/dev/null || need+=("$tool")
done
if [ ${#need[@]} -gt 0 ]; then
  apt-get update -qq >/dev/null || true
  apt-get install -y -qq "${need[@]}" ca-certificates >/dev/null || true
fi
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
