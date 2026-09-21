# fake-gh

Shared fake GitHub CLI for evals that need deterministic pull request state without
network access. Source `setup.sh` from a scenario setup and call `install_gh` to install
`gh` at `/usr/local/bin/gh`.

The fake reports an authenticated CLI and an open PR #48 whose `ty` check is failing.
Every invocation is appended to `/workspace/.fake-gh/calls.log`. Unsupported commands
fail with a diagnostic instead of returning an empty success.
