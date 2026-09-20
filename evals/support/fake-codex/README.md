# fake-codex

Shared pieces for evals of skills that drive the Codex CLI. The eval VM has no Codex, so
each scenario ships its own small `codex` script with canned replies, built on these:

- `lib.sh`: sourced by a scenario's `codex` script. It answers `--version` and
  `login status`, parses `exec` flags into `$MODE` (`implement`, `review` or `resume`)
  and `$CD_DIR`, and logs the call's argv and prompt to `./.fake-codex/calls.log`. It
  provides `edit <path>` (file from stdin) and `reply` (final message from stdin; emits
  Codex's JSONL events, writes `-o`, exits). Set `LOGGED_OUT=1` before sourcing to fail
  auth like a signed-out CLI.
- `setup.sh`: sourced by a scenario's `setup.sh` (identical on both arms). It provides
  `install_codex <script>`, `on_main <path>` (the file's content on `main`, from stdin),
  and `init_repo`, which commits the workspace. With any `on_main` files, it becomes
  branch `feature` on top of them. A `post-commit` hook logs commits to
  `./.fake-codex/commits.log`.

Assertions grade the two logs.
