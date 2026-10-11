# fake-claude-code-remote

Fake `claude-code-remote` MCP server for evals of the cloud-session skills. The eval guest
has no cloud session, so `server.py` (stdlib, stdio) serves the Routine tools those skills
call. Only `list_triggers` and `delete_trigger` exist; their descriptions are copied from the
live server, with `delete_trigger`'s session warning verbatim.

Source `setup.sh` from a scenario's `setup.sh` and call `add_routines <routines.json>`. It
installs `python3` when the guest lacks it and registers the server as the user-scope MCP
server `claude_code_remote` (Claude Code reserves `claude-code-remote`). `routines.json` is a
list of Routines as `list_triggers` shows them; `delete_trigger` removes one for the rest of
the run. Every tool call is appended as a JSON line to
`/workspace/.fake-claude-code-remote/calls.log`.
