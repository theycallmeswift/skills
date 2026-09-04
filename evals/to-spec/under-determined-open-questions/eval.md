---
---

## Prompt

Use the `to-spec` skill to capture this structured-logging design as a spec before
we lose the context. Repo root: your current working directory. We agreed to add
structured JSON logging to the API in `app/server.py`: every request logs method,
path, status, and latency. What we did NOT settle: whether to also log request
bodies (privacy concern, unresolved) and which log sink to ship to.

Today is {TODAY}. No interactive user — proceed end-to-end, then tell me where you
wrote it.

## Assertions

- [ ] Skill `to-spec` invoked
- [ ] A spec file was written at './docs/specs/{TODAY}-<slug>.md' with the full skim-first section set
- [ ] Exactly one `*.md` file exists under './docs/specs/'
- [ ] The two unresolved decisions (whether to log request bodies, and which log sink) appear under '## Open Questions' — phrased as open, not resolved
- [ ] The Problem/Solution/Implementation Decisions sections do NOT invent a confident answer to either open decision (e.g. they do not assert a specific log sink as chosen)
- [ ] The settled parts (logging method/path/status/latency for the request lifecycle in `./app/server.py`) are specified concretely in the substantive sections, so the spec is not hollowed out by deferring everything
