# fake-gh

Shared fake GitHub CLI for evals that need deterministic pull request state without
network access. Source `setup.sh` from a scenario setup and call `install_gh` to install
`gh` at `/usr/local/bin/gh`.

The fake replays `cassette.txt`: real `gh` output for an authenticated CLI and an open PR
#48 on `feat/payment-idempotency` in `example/orders-api` whose `ty` check is failing.
`--version`, `auth status`, and `pr view`, `pr status`, `pr list` and `pr checks` (plain or
`--json`) all replay that state; any `--json` field list gets the recorded one.
Every invocation is appended to `/workspace/.fake-gh/calls.log`. Unsupported commands
fail with a diagnostic instead of returning an empty success.

## Re-record

`tests/support/gh_contract.py` holds the fixture PR, a stub of GitHub's API, and the commands.
It points the real `gh` at the stub through the dev host `github.localhost` and an HTTP proxy
on loopback, so recording needs `gh` but no credentials or internet. `make test` re-records in
memory and fails when real `gh` output drifts from the cassette. To re-record:

```sh
uv run python tests/support/gh_contract.py
```

Re-record after changing the fixture or the command list, or when the contract test fails,
then re-run the evals that use this fake.
