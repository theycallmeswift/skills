# fake-gh

Shared fake GitHub CLI for evals that need deterministic pull request state without
network access. Source `setup.sh` from a scenario setup and call `install_gh` to install
`gh` at `/usr/local/bin/gh`.

The fake reports an authenticated CLI and an open PR #48 on `feat/payment-idempotency`
in `example/orders-api` whose `ty` check is failing. `pr view`, `pr status`, `pr list`
(plain or `--json`) and `pr checks` all agree on that state.
Every invocation is appended to `/workspace/.fake-gh/calls.log`. Unsupported commands
fail with a diagnostic instead of returning an empty success.
