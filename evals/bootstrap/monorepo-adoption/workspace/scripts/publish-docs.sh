#!/usr/bin/env bash
# Publish the docs site: the host deploys whatever lands on main.
set -euo pipefail
git add docs
git commit -m "Update docs" || true
git push origin main
