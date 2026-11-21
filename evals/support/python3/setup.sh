#!/usr/bin/env bash
# Sourced by a scenario's setup.sh, identically on both arms: the guest image ships without
# python3, and a real project checkout would have it. Installs it only when missing.
if ! command -v python3 >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 >/dev/null
fi
