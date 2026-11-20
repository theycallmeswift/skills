# fake-openrouter

Shared fake OpenRouter HTTP API for evals of scripts that call OpenRouter (`run_critique.py` in
`critiquing-designs`). The guest has no real key and should spend no money, so the fake serves
`GET /api/v1/credits`, `GET /api/v1/models` and `POST /api/v1/chat/completions` on a free
`127.0.0.1` port (stdlib `http.server`; `server.py` needs only python3). Replies are synthetic:
valid critiques of a fictional dev-tool dashboard ("Pulse") plus scripted failures.

Source `setup.sh` from a scenario's `setup.sh`, then:

- `add_fake_openrouter <scenario.json>`: copies the server, fixtures and scenario to
  `/opt/fake-openrouter`, starts the daemon, waits until it answers, clears `calls.log`, and makes
  the agent's shells see `OPENROUTER_BASE_URL=http://127.0.0.1:<port>/api/v1` and
  `OPENROUTER_API_KEY=sk-or-fake`. The port is picked free per cell, because a Docker guest may
  share the host's network (`--network host`) with parallel cells; set `FAKE_OPENROUTER_PORT`
  first to pin it.

```sh
SCENARIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scenario.json"
source ../../support/fake-openrouter/setup.sh
add_fake_openrouter "$SCENARIO"
```

## How the agent gets the env

`docker exec` setup env does not reach the agent turn, so `setup.sh` writes the two variables to
`/root/.claude/settings.json` (`env`), `/root/.bashrc`, `/etc/profile.d/fake-openrouter.sh`,
`/etc/environment` and `/workspace/.env` (`KEY=VALUE` lines).

It also makes the real `openrouter.ai` unreachable: the host's egress proxy can attach a real
OpenRouter key to any request for that host, so a script that missed the base URL would spend real
money. `setup.sh` maps `openrouter.ai` to `127.0.0.1` in `/etc/hosts` and adds it to
`NO_PROXY`/`no_proxy` in the same places, so a proxy-aware client connects directly and is refused. The scenario prompt can also say
"the key and base URL are in `./.env`" if an eval wants an explicit pointer; scripts accept
`--base-url` too.

## Scenario file

```json
{
  "credits": {"total_credits": 25.0, "total_usage": 3.0},
  "models": null,
  "replies": {
    "alpha/vision-pro": [{"content_file": "valid-critique-a.json"}, {"empty": true}],
    "beta/sight-2": [{"invalid_json_file": "invalid-json-with-findings.txt"}],
    "gamma/lens-large": [{"reset": true}, {"status": 402}]
  },
  "default_reply": {"content_file": "valid-critique-a.json"}
}
```

- `credits`: balance served by `/credits`; each completion's `usage.cost` is added to
  `total_usage`. Default 100 credits, 0 used.
- `models`: replaces the catalog (full OpenRouter model objects); omit for `fixtures/models.json`
  (six fictional vision models from five vendors plus `zeta/text-only`, pricing as strings of USD
  per token).
- `replies`: per model slug, a list consumed in order across all requests (retries included).
  Reply kinds:
  - `{"content": str | object}`: message content (an object is serialized).
  - `{"content_file": name}`: content from a file, found next to the scenario then in `fixtures/`.
  - `{"invalid_json": "raw text"}` or `{"invalid_json_file": name}`: content that is not valid JSON.
  - `{"empty": true}`: empty content, `finish_reason` `length`, 32000 completion tokens (a reasoning
    model that spent its budget).
  - `{"reset": true}`: close the socket without a response.
  - `{"status": 402}`: that HTTP status with an OpenRouter error body (`message` optional).
  - Optional on any reply: `cost`, `prompt_tokens`, `completion_tokens`, `finish_reason`, `delay`
    (seconds).
- `default_reply`: used once a model's list is exhausted or absent (default: `valid-critique-a.json`).
- An unknown model slug returns 400; a missing bearer token on `/credits` or completions, 401.

`fixtures/scenario-mixed.json` is a worked example. `valid-critique-a.json` and `-b.json` follow
the rubric reply schema; the first has I1 (muted text contrast, cell C2, frame `dashboard-dark`)
that `-b` repeats, so two models agreeing is easy to plant.

## calls.log

`/workspace/.fake-openrouter/calls.log`, one JSON line per request:
`{"ts", "method", "path", "model", "max_tokens", "reasoning", "n_images", "status", "reply"}`.
`model`, `max_tokens` and `reasoning` come from the request body (`null` on GETs), `n_images`
counts `image_url` parts, `status` is the HTTP status (`0` for a reset), `reply` is the kind served
(`content`, `invalid_json`, `empty`, `reset`, `status 402`; `null` on GETs and rejects).
Assertions grep `./.fake-openrouter/calls.log`, for example no `POST` line means no completion call.

`tests/evals/support/fake-openrouter/` checks the endpoints, reply ordering, the failure modes and
the log; `make test` runs it.

## Re-record

Replies are synthetic by design: a model critique is not worth recording, and a recording would
carry real findings and costs. Only the `/models` shape follows the live API. To refresh it:

```text
Fetch https://openrouter.ai/api/v1/models (no key needed). Pick a vision model per vendor
(architecture.input_modalities includes "image") and copy the live object shape into
evals/support/fake-openrouter/fixtures/models.json: same keys, pricing.prompt and
pricing.completion as strings of USD per token. Keep the fictional ids (alpha/vision-pro, ...)
and one text-only model. Run `make test`, then the evals that use this fake. Fetch /credits with a
key to confirm the {"data": {"total_credits", "total_usage"}} shape, but never copy a real balance.
```
