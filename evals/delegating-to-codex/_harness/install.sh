#!/usr/bin/env bash
# Shared per-cell setup for delegating-to-codex evals, identical on every arm: installs the
# tools the skill's script needs, puts a fake `codex` on PATH with this scenario's canned
# replies, and turns /workspace into a git repo. Run from a scenario's setup.sh as
#   bash ../_harness/install.sh
# with the scenario folder as cwd. Optional scenario inputs:
#   fake/<mode>/{last.md,files/}  canned Codex output per mode (implement, review, resume)
#   fake/logged-out               make `codex login status` fail
#   base/                         files for the `main` commit; the seeded workspace then
#                                 lands as a second commit on branch `feature`
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

need=()
command -v python3 >/dev/null || need+=(python3)
command -v git >/dev/null || need+=(git)
if [ ${#need[@]} -gt 0 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null
  apt-get install -y -qq "${need[@]}" >/dev/null
fi

install -m 0755 "$here/fake-codex" /usr/local/bin/codex
rm -rf /opt/fake-codex && mkdir -p /opt/fake-codex
[ -d fake ] && cp -R fake/. /opt/fake-codex/

git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global init.defaultBranch main
git config --global --add safe.directory /workspace

cd /workspace
git init -q
printf '.fake-codex/\n' >> .git/info/exclude
if [ -d "$OLDPWD/base" ]; then
  snap="$(mktemp -d)"; cp -R /workspace/. "$snap/"; rm -rf "$snap/.git"
  find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cp -R "$OLDPWD/base/." /workspace/
  git add -A && git commit -qm "Initial commit"
  git checkout -qb feature
  find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cp -R "$snap/." /workspace/
  git add -A && git commit -qm "Feature work"
else
  git add -A && git commit -qm "Initial commit"
fi

cat > .git/hooks/post-commit <<'HOOK'
#!/usr/bin/env bash
mkdir -p /workspace/.fake-codex
git log -1 --format='commit %h %s' --name-only >> /workspace/.fake-codex/commits.log
HOOK
chmod +x .git/hooks/post-commit
