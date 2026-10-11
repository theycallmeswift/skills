#!/usr/bin/env bash
set -euo pipefail

# The skill's helper is a stdlib Python script; install the interpreter on both arms alike.
if ! command -v python3 >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
fi

# No GitHub here: gh logs every call, then fails the way the real gh does offline.
cat > /usr/local/bin/gh <<'GH'
#!/usr/bin/env bash
mkdir -p /workspace/.fake-gh
{ printf 'gh'; printf ' %q' "$@"; printf '\n'; } >> /workspace/.fake-gh/calls.log
echo "error connecting to api.github.com" >&2
echo "check your internet connection or https://githubstatus.com" >&2
exit 1
GH
chmod 0755 /usr/local/bin/gh
