#!/usr/bin/env bash
set -euo pipefail

if ! command -v git >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git >/dev/null
fi

git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global --add safe.directory '*'

branch="claude/bootstrap-spendsheet-k2r9xa"
origin="/srv/spendsheet.git"
# The judge reads every file under /workspace as text, and a small loose git object
# can decode as text with NUL bytes, so the git dir lives outside it.
gitdir="/srv/spendsheet-workspace.git"
# The judge sees only /workspace, so the remote mirrors its branches here on each push.
report="/workspace/.fake-origin/branches.txt"

# A fresh hosted repo: the agent's working branch is its only branch, and the default.
git init -q --bare "$origin"
git -C "$origin" symbolic-ref HEAD "refs/heads/$branch"

cd /workspace
git init -q --template= --separate-git-dir="$gitdir" -b "$branch"
mkdir -p "$gitdir/info"
printf '.fake-origin/\n' >> "$gitdir/info/exclude"
git add README.md
git commit -qm "Add README"
git remote add origin "$origin"
git push -q -u origin "$branch"

cat > "$origin/hooks/post-receive" <<HOOK
#!/usr/bin/env bash
mkdir -p "$(dirname "$report")"
for ref in \$(git for-each-ref --format='%(refname:short)' refs/heads); do
  printf 'branch %s\n' "\$ref"
  printf '  tip parents: %s\n' "\$(git rev-list --parents -n 1 "\$ref" | wc -w | awk '{print \$1 - 1}')"
  printf '  commits: %s\n' "\$(git rev-list --count "\$ref")"
  printf '  files:\n'
  git ls-tree -r --name-only "\$ref" | sed 's/^/    /'
done > "$report"
HOOK
chmod +x "$origin/hooks/post-receive"

fail() {
  printf 'unexpected fresh-repo-no-main fixture: %s\n' "$1" >&2
  exit 1
}

[ "$(git ls-remote --heads origin)" = "$(git rev-parse HEAD)	refs/heads/$branch" ] || fail "remote branches"
[ "$(git rev-parse --abbrev-ref '@{u}')" = "origin/$branch" ] || fail "upstream"
[ -z "$(git status --porcelain)" ] || fail "dirty tree"
