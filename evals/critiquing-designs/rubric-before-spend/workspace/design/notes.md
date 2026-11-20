# Pulse design notes

Pulse is our internal deploy and incident dashboard. The people who use it are on-call and release
engineers, usually on a laptop in a dark room during a deploy or an incident.

## Decided

- Dark theme only for v1. No light theme work this quarter (decided 2026-09-14).
- The left nav stays collapsed to icons by default and expands on hover: people wanted the width
  for the deploys table (decided 2026-10-02).
- The deploys table shows 20 rows per page. No infinite scroll: people link to page 2 in incident
  channels (decided 2026-10-02).

## Open

- Does the dashboard make a failed deploy obvious enough?
- The Incidents empty state feels like a dead end.
