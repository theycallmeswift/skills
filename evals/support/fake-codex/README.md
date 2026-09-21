# fake-codex

Shared pieces for evals of skills that drive the Codex CLI. The eval VM has no Codex, so
each scenario ships its own small `codex` script with canned replies, built on these:

- `lib.sh`: sourced by a scenario's `codex` script. It answers `--version` and
  `login status`, parses the `exec` argv into `$CD_DIR`, `$SANDBOX` (from `--sandbox`, or
  from `-c sandbox_mode=` on a resumed thread, which takes no `--sandbox` flag) and
  `$MODE` — `resume` for `exec resume`, `review` for a fresh read-only dispatch,
  `implement` otherwise — and logs the call's argv and prompt to `./.fake-codex/calls.log`.
  It provides `edit <path>` (file from stdin, refused under a read-only sandbox) and
  `reply` (final message from stdin; emits Codex's JSONL events, writes `-o`, exits). Set
  `LOGGED_OUT=1` before sourcing to fail auth like a signed-out CLI, and
  `FAKE_CODEX_LOG_DIR` to run a fake by hand outside the VM's `/workspace`.
- `setup.sh`: sourced by a scenario's `setup.sh` (identical on both arms). It provides
  `install_codex <script>`, `on_main <path>` (the file's content on `main`, from stdin),
  and `init_repo`, which commits the workspace. With any `on_main` files, it becomes
  branch `feature` on top of them. A `post-commit` hook logs commits to
  `./.fake-codex/commits.log`.

Assertions grade the two logs.
