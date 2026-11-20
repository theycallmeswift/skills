#!/usr/bin/env bash
set -euo pipefail

source ../../support/fake-openrouter/setup.sh
add_fake_openrouter "$PWD/scenario.json"
