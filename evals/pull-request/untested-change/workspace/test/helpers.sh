# Sourced by every test file.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
printf '%s %s\n' "$(date -u +%FT%TZ)" "$(basename "$0")" >> "$here/.test-runs.log"

failures=0
assert_eq() {
  if [ "$1" = "$2" ]; then
    printf 'ok   %s\n' "$3"
  else
    printf 'FAIL %s: expected %q, got %q\n' "$3" "$2" "$1"
    failures=$((failures + 1))
  fi
}
