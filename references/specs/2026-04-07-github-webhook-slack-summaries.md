# GitHub Webhook to Slack PR Summaries

**Date:** 2026-04-07
**Status:** Draft

## Goal
Listen for GitHub PR events via webhook and post concise summaries to Slack, so the team sees PR activity where they already work. Configurable per-repo and per-channel, with retries so a flaky Slack call doesn't lose a message.

## Non-Goals
- Two-way interaction (no Slack-to-GitHub actions)
- Review assignment or bot commenting on PRs
- Historical backfill of past PRs
- A web UI for configuration (YAML config file only)

## Approach
Run a small Node.js HTTP service that verifies GitHub's HMAC signature, enqueues the event in an in-process BullMQ queue backed by Redis, and has a worker that formats the summary and posts to Slack with exponential backoff retries. Repo -> channel routing lives in a single `config.yml` file loaded at startup. This is the simplest design that satisfies retries without losing events on crash (Redis persistence) and keeps per-channel config trivial.

Alternatives considered:
1. **Serverless (AWS Lambda + SQS)** -- more ops overhead and cold starts for a low-volume internal tool. Rejected.
2. **Pure in-memory queue (no Redis)** -- simplest, but a crash mid-retry drops events. Rejected because retries are a stated requirement.
3. **Recommended: Node service + Redis/BullMQ** -- smallest reliable design.

## Components
- `src/server.ts` -- Express/Fastify endpoint at `POST /webhook/github`, verifies signature, enqueues job
- `src/queue.ts` -- BullMQ queue + worker setup
- `src/slack.ts` -- Slack Web API client wrapper, posts formatted message
- `src/format.ts` -- turns a PR event payload into a Slack message (blocks)
- `src/config.ts` -- loads `config.yml`, validates with zod
- `config.yml` -- repo -> channel map, event filters
- `.env.example` -- `GITHUB_WEBHOOK_SECRET`, `SLACK_BOT_TOKEN`, `REDIS_URL`

## Data / Interfaces
- Webhook handler input: GitHub `pull_request` event payload
- Queue job shape: `{ repo: string, action: string, pr: { number, title, url, author, base, head } }`
- Config shape:
  ```yaml
  repos:
    mlh/website:
      channel: "#eng-website"
      events: [opened, closed, ready_for_review]
  ```
- Slack output: a single message with title, author, link, and action

## Testing
- Unit tests for `format.ts` (payload -> Slack blocks) and `config.ts` (valid + invalid configs)
- Integration test that hits `/webhook/github` with a fixture payload, asserts the job lands in the queue
- Manual check: send a test PR event from a sandbox repo, verify it shows up in a test Slack channel
- Retries left unverified beyond BullMQ's own tests; we rely on the library's guarantees

## Open Questions
- Do we want to filter draft PRs by default, or leave that to per-repo config?
- Should we dedupe rapid edits to the same PR within a short window?

---

## Self-Review

Scanned for placeholders, contradictions, ambiguity, and scope creep:
- No TBDs or TODOs remain
- Components and data shapes are consistent with the approach
- Retries requirement is satisfied by BullMQ (addressed the "pure in-memory" rejection)
- Scope is focused on a single service; no unrelated refactoring pulled in
- Open questions are flagged, not hidden

## Next

Spec is written to `docs/specs/2026-04-07-github-webhook-slack-summaries.md`. Please review and let me know if you want to change anything before we move on.

Once you approve, here are the options for what's next:
1. Write an implementation plan that breaks this into actionable steps
2. Scope another piece of MechaSwift (e.g. the config reload story, or alerting)
3. Something else -- your call
