# Scope Rubric

Evaluated by `make eval`.

## Critical

- Output proposes 2-3 distinct approaches with trade-offs (when generating a design)
- Output includes a clear recommendation with reasoning for which approach to use
- Output asks the user to review the spec before proceeding
- A spec file is written to references/specs/ with a descriptive name (for the github-webhook-slack case)
- Written spec mentions per-repo to channel routing (allowlist, routing table, or equivalent)
- Written spec specifies a durable queue or retry mechanism (Redis, BullMQ, persistent queue)
- Written spec lists all three event types: opened, ready_for_review, closed
- Written spec marks the user-stated non-goals as out of scope, naming each one
- Written spec deployment target is Fly.io and the runtime is Node.js
- Written spec mentions YAML config loaded at startup
- For `vague-notifications`: output does not propose a full design or write a spec without first gathering requirements
- For `skip-design-rate-limiter`: output does NOT agree to skip scoping — it pushes back and asks a clarifying question
- For `skip-design-rate-limiter`: output acknowledges the user's urgency AND names a concrete risk of jumping in blind

## Optional

- Output includes a self-review step scanning for placeholders or contradictions
- Output offers what's-next options (implementation plan, scope another piece, etc.)
