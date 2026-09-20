#!/usr/bin/env bash
# Sourced by a scenario's setup.sh, which runs from the scenario folder inside the eval VM
# before the agent starts, identically on both arms. See README.md.
set -euo pipefail
FAKE_CODEX_SUPPORT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_DIR="$(mktemp -d)"

# install_codex <script>: the scenario's fake on PATH as `codex`, plus python3 and git.
install_codex() {
  local need=()
  command -v python3 >/dev/null || need+=(python3)
  command -v git >/dev/null || need+=(git)
  if [ ${#need[@]} -gt 0 ]; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}" >/dev/null
  fi
  mkdir -p /opt/fake-codex
  cp "$FAKE_CODEX_SUPPORT/lib.sh" /opt/fake-codex/lib.sh
  install -m 0755 "$1" /usr/local/bin/codex
  git config --global user.name "Eval User"
  git config --global user.email "eval@example.com"
  git config --global init.defaultBranch main
  git config --global --add safe.directory /workspace
}

# on_main <path>: stdin is <path>'s content on `main`, before the feature branch.
on_main() { mkdir -p "$(dirname "$MAIN_DIR/$1")"; cat > "$MAIN_DIR/$1"; }

# init_repo: commit /workspace. With on_main files, `main` holds those and the seeded
# workspace lands as branch `feature` on top.
init_repo() {
  cd /workspace
  git init -q
  printf '.fake-codex/\n' >> .git/info/exclude
  if [ -n "$(ls -A "$MAIN_DIR")" ]; then
    local feature; feature="$(mktemp -d)"
    cp -R /workspace/. "$feature/"; rm -rf "$feature/.git"
    find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
    cp -R "$MAIN_DIR/." /workspace/
    git add -A && git commit -qm "Initial commit"
    git checkout -qb feature
    find /workspace -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
    cp -R "$feature/." /workspace/
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
}
