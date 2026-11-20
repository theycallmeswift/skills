# Cloud agents

Set up a Linux cloud VM so a coding agent can build and verify this repo.

## What the VM needs

- **Node 26,** installed beside the image's own.
- **Python 3.13 through uv,** which installs from `astral.sh` and
  `github.com` and fetches packages from `pypi.org` and
  `files.pythonhosted.org`.
- **Network access** to `nodejs.org`, `registry.npmjs.org`, `github.com` for
  the skills plugin, and the image's apt mirrors when `libatomic1` is
  missing.
- **The `claude` CLI** on the image, for the plugin install. Claude Code
  cloud images ship it.
- **No secrets.** `<test>` and `<lint>` need no credentials.

## 1. Setup script

Paste this into the service's setup-script field. It runs as root, installs
Node 26 into `/opt/node26` with its checksum verified, installs the
`core@mechaswift` plugin that `.claude/settings.json` enables, and is safe to
run twice. A failed download exits non-zero and stops the session, since a
session without its tools can't verify anything.

```bash
#!/bin/bash
set -euo pipefail

# Python only: uv installs the Python version itself.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

NODE_DIR=/opt/node26
RELEASES=https://nodejs.org/dist/latest-v26.x

case "$(uname -m)" in
  x86_64) arch=x64 ;;
  aarch64 | arm64) arch=arm64 ;;
  *) echo "unsupported CPU: $(uname -m)" >&2; exit 1 ;;
esac

# Node's Linux binaries link against libatomic, which minimal images omit.
if ! ldconfig -p | grep -q 'libatomic\.so\.1'; then
  apt-get update -qq && apt-get install -y -qq libatomic1
fi

if [ ! -x "$NODE_DIR/bin/node" ]; then
  download_dir="$(mktemp -d)"
  cd "$download_dir"
  curl -fsSLO "$RELEASES/SHASUMS256.txt"
  tarball="$(awk -v name="linux-$arch.tar.xz" '$2 ~ name "$" { print $2 }' SHASUMS256.txt)"
  curl -fsSLO "$RELEASES/$tarball"
  grep " $tarball\$" SHASUMS256.txt | sha256sum -c -
  mkdir -p "$NODE_DIR"
  tar -xJf "$tarball" -C "$NODE_DIR" --strip-components=1
  cd /
  rm -rf "$download_dir"
fi

ln -sf "$NODE_DIR/bin/node" "$NODE_DIR/bin/npm" "$NODE_DIR/bin/npx" /usr/local/bin/
"$NODE_DIR/bin/node" --version

# The house skills plugin. Enabling it in .claude/settings.json only declares
# intent; each container must install it. Both commands are safe to repeat.
if ! claude plugin marketplace list 2>/dev/null | grep -q mechaswift; then
  claude plugin marketplace add theycallmeswift/skills
fi
claude plugin install core@mechaswift
claude plugin list | grep -A 3 'core@mechaswift'
```

## 2. Each session

Dependencies track the lockfile, which changes after the image is cached, so
install them in each session from the repository root:

```bash
node --version
<install>
```

If `node --version` prints something older than 26, prefix each command that
reaches Node with `PATH="/opt/node26/bin:$PATH"`, since agent shells may drop
an `export` between commands.

## 3. Verify

```bash
<test>
<lint>
```

Both pass without credentials once steps 1 and 2 are done.

## Claude Code on the web

Configure the environment at [claude.ai/code](https://claude.ai/code); the
[cloud environments](https://code.claude.com/docs/en/cloud-environments) page
is the reference.

- **Setup script:** paste step 1. Its result is cached for later sessions
  until the script or network settings change. Keep it under about five
  minutes. The cache also pins the plugin version it installed; to pick up a
  newer `core@mechaswift`, edit the script (a comment will do) so it reruns.
- **Node on `PATH`:** the image's own Node comes first on `PATH`. The
  SessionStart hook
  [`claude-cloud-node26-path.sh`](../.claude/hooks/claude-cloud-node26-path.sh)
  puts Node 26 first in cloud sessions only.
- **Network access:** unless the level is **Full**, allow every host in
  [What the VM needs](#what-the-vm-needs).
- **Environment variables:** leave them empty.
