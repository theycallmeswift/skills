#!/usr/bin/env bash
# Run every test file; exit non-zero if any fails.
cd "$(dirname "$0")/.."
status=0
for t in test/*_test.sh; do
  bash "$t" || status=1
done
exit "$status"
