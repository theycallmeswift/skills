# fake-claude-code-remote

Fake `claude-code-remote` MCP server for evals of the cloud-session skills. The eval guest
has no cloud session, so `server.py` (stdlib, stdio) replays the Routine tools those skills
call from `cassette.json`, recorded from the live server: the verbatim `list_triggers` and
`delete_trigger` definitions, the `list_triggers` envelope, and one scrubbed Routine.

Source `setup.sh` from a scenario's `setup.sh` and call `add_routines <routines.json>`. It
installs `python3` when the guest lacks it and registers the server as the user-scope MCP
server `claude_code_remote` (Claude Code reserves `claude-code-remote`). `routines.json` lists
only the fields a scenario sets; each Routine is laid over the recorded one, so every live
field is present. `delete_trigger` removes one for the rest of the run and echoes it under
`trigger`. Every tool call is appended as a JSON line to
`/workspace/.fake-claude-code-remote/calls.log`.

## Re-record

Re-record when the orchestrator or worker skill, or an eval using this fake, changes. Run in a
Claude Code cloud session with this repo checked out:

```text
Re-record evals/support/fake-claude-code-remote/cassette.json from the live claude-code-remote
MCP server.
1. tools: copy the live list_triggers and delete_trigger definitions (name, description, full
   input schema) exactly as your tool list shows them. No paraphrasing or trimming.
2. Call list_triggers with limit 3 (read-only). Never call delete_trigger, create_trigger, or
   any other tool that writes. Set list_triggers to the response envelope with data emptied,
   and routine to one returned Routine with every field, preferring one that has last_run.
3. Scrub: replace every real ID, account uuid, session id, name, prompt, cursor, and timestamp
   with fixture values. No real account data may land in the repo.
4. Set recorded to today's date and update the date in docs/evals/claude-cloud-orchestrator.md.
5. Run make test, make lint, make evals:lint, then re-run the evals that use this fake.
```
