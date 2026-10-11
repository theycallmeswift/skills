#!/usr/bin/env bash
# Sourced by a scenario's setup.sh before the agent starts. See README.md.

install_gh() {
  local install_dir="${FAKE_GH_INSTALL_DIR:-/usr/local/bin}"
  local support
  support="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  mkdir -p /opt/fake-gh "$install_dir"
  install -m 0755 "$support/gh" /opt/fake-gh/gh
  install -m 0644 "$support/cassette.txt" /opt/fake-gh/cassette.txt
  ln -sf /opt/fake-gh/gh "$install_dir/gh"

  if [ "$install_dir" != "/usr/local/bin" ]; then
    PATH="$install_dir:$PATH"
    export PATH
  fi
}
