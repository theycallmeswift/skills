#!/usr/bin/env bash
# Sourced by a scenario's fake `codex` script. See README.md.
set -euo pipefail
LOG_DIR=/workspace/.fake-codex
THREAD=0199a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b
LOGGED_OUT="${LOGGED_OUT:-0}"

case "${1:-}" in
  --version) echo "codex-cli 0.144.1"; exit 0 ;;
  login)
    if [ "${2:-}" = status ] && [ "$LOGGED_OUT" = 0 ]; then echo "Logged in using ChatGPT"; exit 0; fi
    echo "Not logged in" >&2; exit 1 ;;
  exec) shift ;;
  *) echo "fake codex: unsupported command: $*" >&2; exit 2 ;;
esac

MODE=implement; OUT=""; CD_DIR="$PWD"; PROMPT=""; DASH=0; ARGS=("$@")
if [ "${1:-}" = resume ]; then MODE=resume; fi
index=0
while [ $index -lt ${#ARGS[@]} ]; do
  argument="${ARGS[$index]}"
  case "$argument" in
    -o|--output-last-message) index=$((index+1)); OUT="${ARGS[$index]}" ;;
    -C|--cd) index=$((index+1)); CD_DIR="${ARGS[$index]}" ;;
    -s|--sandbox)
      index=$((index+1))
      if [ "${ARGS[$index]}" = read-only ] && [ "$MODE" != resume ]; then MODE=review; fi
      ;;
    --output-schema|-m|--model|-p|--profile|-i|--image|--color|-c|--config|--add-dir|--enable|--disable)
      index=$((index+1)) ;;
    -) DASH=1 ;;
    -*|resume) ;;
    *) PROMPT="$a" ;;
  esac
  index=$((index+1))
done
# Like the real CLI: the prompt comes from stdin for `-`, or when no prompt argument is given.
if [ $DASH = 1 ] || [ -z "$PROMPT" ]; then PROMPT="$(cat)"; fi

mkdir -p "$LOG_DIR"
{
  echo "=== codex exec call (mode: $MODE) ==="
  echo "argv: codex exec ${ARGS[*]}"
  echo "--- prompt ---"
  printf '%s\n' "$PROMPT"
  echo "--- end prompt ---"
} >> "$LOG_DIR/calls.log"

if [ "$LOGGED_OUT" = 1 ]; then
  echo '{"type":"error","message":"Not logged in. Run `codex login` to authenticate."}'
  echo 'Error: Not logged in. Run `codex login` to authenticate.' >&2
  exit 1
fi

# edit <path>: write stdin to <path> in the worktree, as Codex's edit.
edit() { mkdir -p "$(dirname "$CD_DIR/$1")"; cat > "$CD_DIR/$1"; }

# reply: stdin is Codex's final message. Emits the JSONL stream and exits.
reply() {
  local text; text="$(cat)"
  sleep 2
  if [ -n "$OUT" ]; then printf '%s\n' "$text" > "$OUT"; fi
  local json; json="$(printf '%s' "$text" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS="\\n"} {print}')"
  echo "{\"type\":\"thread.started\",\"thread_id\":\"$THREAD\"}"
  echo '{"type":"turn.started"}'
  echo "{\"type\":\"item.completed\",\"item\":{\"id\":\"item_0\",\"type\":\"agent_message\",\"text\":\"$json\"}}"
  echo '{"type":"turn.completed","usage":{"input_tokens":41210,"cached_input_tokens":30720,"output_tokens":2210,"reasoning_output_tokens":640}}'
  exit 0
}
