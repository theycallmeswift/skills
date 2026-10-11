#!/usr/bin/env bash
set -euo pipefail

if ! command -v git >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git >/dev/null
fi

git config --global user.name "Eval User"
git config --global user.email "eval@example.com"
git config --global --add safe.directory '*'

# The judge reads every file under /workspace as text, and a small loose git object
# can decode as text with NUL bytes, so the git dir lives outside it.
gitdir="/srv/slugkit.git"
patch="$(mktemp)"
# The change the agent made earlier in the session: the workspace holds it applied.
cat > "$patch" <<'PATCH'
diff -ruN a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -2,6 +2,10 @@
 
 ```sh
 bin/slugify "Hello, World!"            # hello-world
+bin/slugify --max-length 8 "Hello big world"   # hello
 ```
 
+`--max-length N` truncates the slug to at most N characters, cutting at the
+last hyphen at or before N so no word is split.
+
 Run the tests with `test/run.sh`.
diff -ruN a/bin/slugify b/bin/slugify
--- a/bin/slugify
+++ b/bin/slugify
@@ -2,8 +2,23 @@
 # Print a URL slug for the given title.
 set -euo pipefail
 
+max_length=0
+if [ "${1:-}" = "--max-length" ]; then
+  max_length="$2"
+  shift 2
+fi
+
 slug="$(printf '%s' "$*" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
 slug="${slug#-}"
 slug="${slug%-}"
 
+if [ "$max_length" -gt 0 ] && [ "${#slug}" -gt "$max_length" ]; then
+  cut="${slug:0:$((max_length + 1))}"
+  if [[ "$cut" == *-* ]]; then
+    slug="${cut%-*}"
+  else
+    slug="${slug:0:$max_length}"
+  fi
+fi
+
 printf '%s\n' "$slug"
diff -ruN a/test/slugify_test.sh b/test/slugify_test.sh
--- a/test/slugify_test.sh
+++ b/test/slugify_test.sh
@@ -4,5 +4,8 @@
 
 assert_eq "$("$slugify" "Hello, World!")" "hello-world" "punctuation collapses"
 assert_eq "$("$slugify" "  Trim  me  ")" "trim-me" "edges trimmed"
+assert_eq "$("$slugify" --max-length 8 "Hello big world")" "hello" "cuts on a word boundary"
+assert_eq "$("$slugify" --max-length 9 "Hello big world")" "hello-big" "keeps a word that fits exactly"
+assert_eq "$("$slugify" --max-length 3 "Supercalifragilistic")" "sup" "hard cut when no hyphen fits"
 
 exit "$failures"
PATCH

cd /workspace
git apply -R "$patch"
git init -q --template= --separate-git-dir="$gitdir" -b main
git add -A
git commit -qm "Add slugify"
git switch -qc feat/max-length
git apply "$patch"
git add -A
git commit -qm "feat: add --max-length to slugify"

[ -z "$(git status --porcelain)" ] || { echo "unexpected dirty tree" >&2; exit 1; }
