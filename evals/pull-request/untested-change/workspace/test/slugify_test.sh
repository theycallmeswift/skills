#!/usr/bin/env bash
source "$(dirname "$0")/helpers.sh"
slugify="$here/bin/slugify"

assert_eq "$("$slugify" "Hello, World!")" "hello-world" "punctuation collapses"
assert_eq "$("$slugify" "  Trim  me  ")" "trim-me" "edges trimmed"
assert_eq "$("$slugify" --max-length 8 "Hello big world")" "hello" "cuts on a word boundary"
assert_eq "$("$slugify" --max-length 9 "Hello big world")" "hello-big" "keeps a word that fits exactly"
assert_eq "$("$slugify" --max-length 3 "Supercalifragilistic")" "sup" "hard cut when no hyphen fits"

exit "$failures"
