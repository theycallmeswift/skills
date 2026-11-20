#!/usr/bin/env bash
set -euo pipefail

# No add_google_workspace_skill: this scenario is the agent without it.
source ../../support/fake-google-slides/setup.sh
add_google_slides
