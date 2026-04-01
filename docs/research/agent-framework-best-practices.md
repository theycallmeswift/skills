# Agent Framework Best Practices

Research compiled for the MechaSwift project. Synthesized from analysis of 6 production agent frameworks (ai-agent-blueprint, compound-engineering-plugin, get-shit-done, superpowers, claude-md-template-pack, ai-playbook-ops) and supplementary web research on context engineering, multi-agent orchestration, and coding agent architecture.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Agent Configuration](#2-agent-configuration)
3. [Skills System Design](#3-skills-system-design)
4. [Context Engineering](#4-context-engineering)
5. [Memory Architecture](#5-memory-architecture)
6. [Multi-Agent Orchestration](#6-multi-agent-orchestration)
7. [Workflow Design](#7-workflow-design)
8. [Hooks and Commands](#8-hooks-and-commands)
9. [Code Review and Quality](#9-code-review-and-quality)
10. [Cross-Platform Compatibility](#10-cross-platform-compatibility)
11. [Self-Improvement and Learning](#11-self-improvement-and-learning)
12. [Key Principles](#12-key-principles)

---

## 1. Executive Summary

Across all six frameworks studied, a consistent architecture emerges: **structure beats prompts, fresh contexts prevent degradation, and verification gates ensure quality**. The most effective agent systems share these characteristics:

- **Layered configuration**: Global identity + project-specific capabilities
- **On-demand skills**: Loaded when relevant, not stuffed into every session
- **Atomic task decomposition**: Work broken into 2-5 minute independently verifiable pieces
- **Multi-agent orchestration**: Parallel execution with fresh context per task
- **Staged verification**: Hard gates between design, planning, execution, and review
- **File-based state**: The filesystem is the source of truth, not the context window

The single most impactful insight: **context engineering matters more than capability engineering**. Better structured input to existing models consistently outperforms adding new capabilities with poor context.

---

## 2. Agent Configuration

### Dual Configuration Architecture

All production frameworks use a two-layer configuration system:

**Global config** (`~/.claude/CLAUDE.md`):
- Agent identity, values, communication style
- Self-improvement rules and decision-making boundaries
- Stable across all projects
- Should stay under 300 lines

**Project config** (project-level `CLAUDE.md`):
- Project-specific capabilities, tools, and integrations
- Available skills and behavioral rules
- Secrets locations and environment setup
- Changes per-project

This separation enables consistent identity with context-specific capabilities.

### Configuration Best Practices

**Keep it lean.** CLAUDE.md loads every session and consumes context. For each line, ask: "Would removing this cause mistakes?" Only include conventions the agent would otherwise get wrong. One practitioner reduced their config from 471 lines to 61 over 1000+ sessions, proving that lean consistently outperforms comprehensive. The goal is a routing layer, not a documentation dump.

**Config as routing layer.** CLAUDE.md should contain identity, principles, and pointers to detailed docs. Don't inline reference material that's only needed in specific contexts. Point to it instead and let skills or workflows load it on demand. This applies the same progressive disclosure pattern used in skills to the config itself.

**"Working With Me" section.** The most effective configs include a section about the human: who they are, what they do, how they prefer to work, and what their decision-making values are. This isn't decoration. It guides the agent's decisions about when to ask vs execute, how formal to be, and what context to prioritize. Think of it as a role definition for the human, not just the agent.

**Principles over rules.** "Prefer reversible actions" outperforms any enumerated list of dangerous commands. Agents generalize from principles but can't extrapolate from incomplete rule sets. When writing config, state the principle and the reasoning behind it. An agent that understands *why* will handle edge cases a rule list can't anticipate.

**Concrete behaviors over adjectives.** "Be thorough" is useless. "Before claiming completion, run it and show me output" is actionable. Every instruction in CLAUDE.md should describe an observable behavior, not a quality aspiration. If you can't tell whether the agent followed the instruction by looking at its output, the instruction needs to be rewritten.

**Don't duplicate linters.** Formatting rules belong in deterministic tools (ESLint, Prettier, Ruff), not in CLAUDE.md. Linters are cheaper, faster, and more reliable than LLM-based enforcement.

**Role-based templates work well.** The claude-md-template-pack demonstrates that different roles (solo developer, team lead, devops engineer) need fundamentally different autonomy levels, safety rails, and domain knowledge. A devops engineer template emphasizes blast-radius awareness; a solo developer template maximizes autonomy.

**Multi-agent compatibility.** For frameworks targeting multiple agents, maintain both CLAUDE.md (Claude-specific) and AGENTS.md (universal standard). The AGENTS.md format has been adopted by 60k+ projects via the Linux Foundation.

### Autonomy Levels

The template-pack framework defines graduated autonomy:

| Level | Description | Example |
|-------|-------------|---------|
| Full autonomy | Act without asking | Read files, run tests, format code |
| Confirm first | Describe plan, wait for approval | Architectural changes, dependency updates |
| Never autonomous | Always require human action | Production deployments, credential handling |

The appropriate level depends on reversibility and blast radius of the action.

---

## 3. Skills System Design

### What Skills Are

Skills are **on-demand capability modules** that load into the agent's context when relevant. Unlike CLAUDE.md (always loaded), skills activate selectively, keeping the context window lean.

### File Format

Every skill follows this structure:

```
skill-name/
  SKILL.md          # Main skill definition (under 2,000 tokens)
  references/       # On-demand reference files
  scripts/          # Executable scripts
  templates/        # Output templates
  docs/             # Extended documentation
```

SKILL.md uses YAML frontmatter:

```yaml
---
name: skill-name
description: What it does + when to use it (under 1024 chars)
allowed-tools: [optional tool restrictions]
---
```

### Activation and Description Design

Skill activation rates vary dramatically based on description quality:

| Description Quality | Activation Rate |
|---------------------|----------------|
| Unoptimized | ~20% |
| Optimized keywords | ~50% |
| Keywords + examples | 72-90% |
| Hook-based forced evaluation | 84% |

**Description formula**: Third person, two-part structure:
1. What it does
2. When to use it (specific trigger keywords and file types)

Example: "Use when implementing any feature or bugfix, before writing implementation code"

### Naming Conventions

- Use **kebab-case** for skill directories: `test-driven-development`, `systematic-debugging`
- Use **gerund form** for clarity: `processing-pdfs`, `managing-databases`
- Prefix with namespace when plugins coexist: `compound-engineering:ce-brainstorm`

### Reference File Loading

Two mechanisms for including additional context:

**On-demand** (backtick paths): Loaded only when the skill needs them. Keeps the main skill lean.
```markdown
Load this reference on demand: `references/schema.json`
```

**Embedded** (`@` syntax): Small required files (<150 lines) included at load time.
```markdown
@./references/output-contract.json
```

### Skill Design Patterns

**Hard gates**: Skills that enforce workflow discipline use "iron laws" — violations require starting over, no exceptions. The TDD skill mandates: "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST."

**Anti-pattern tables**: Effective skills include tables of what NOT to do, making violations easy to detect.

**Red flag detection**: Skills list rationalizations that signal the agent is about to bypass the skill's intent (e.g., "This is just a simple change" → still follow the process).

**Process flows**: Skills define explicit state machines with transitions between phases. Each phase has entry criteria, actions, and exit criteria.

**Checklists**: Self-review checklists at the end of skills catch common omissions before the agent claims completion.

### Beta Skills

Use a `-beta` suffix with `disable-model-invocation: true` to prevent accidental triggering during development. Promotion path: develop as beta → validate across sessions → promote to stable → deprecate beta.

---

## 4. Context Engineering

### Why Context Engineering Matters

Context engineering is the practice of structuring what information the agent receives, when it receives it, and how it's formatted. This has more impact on agent quality than model selection or prompt engineering.

### KV-Cache Optimization

**KV-cache hit rate is the single most important production metric.** Cached tokens cost ~10x less than uncached ones. To maximize cache hits:

- Maintain stable prompt prefixes (don't shuffle system prompt content)
- Design append-only contexts where possible
- Ensure deterministic JSON serialization
- Keep CLAUDE.md stable between sessions

### File System as Externalized Memory

The Manus agent (web research agent handling ~50 tool calls per task) proved that **treating the filesystem as unlimited persistent context** outperforms in-context compression. Instead of compressing observations into the context window, write intermediate results to files and reference them.

Key principle: Compression stays reversible — drop content from context if the URL/path remains available for re-reading.

### The Todo Attention Trick

Maintain a progress file (todo.md, STATE.md) that gets updated step-by-step. This recites objectives into the end of context, pushing plans into the model's recent attention window and fighting "lost-in-the-middle" degradation.

This is why all studied frameworks maintain explicit state files that are read and updated throughout execution.

### Tool Design for Context Efficiency

- **Minimize functional overlap** between tools — overlapping tools confuse tool selection
- **Use naming conventions** for prefix-based filtering: `browser_*`, `shell_*`, `file_*`
- **Return token-efficient information** — tools that return 10,000 tokens of irrelevant data waste context
- **Prefer native tools** (Glob, Grep, Read, Edit) over shell commands — they're more context-efficient and reviewable

### Context Rot Prevention

"Quality degradation that happens as Claude fills its context window" — the get-shit-done framework's core problem statement.

Solutions observed across frameworks:
- Fresh 200k context per plan/task (get-shit-done)
- Subagent-per-task execution (superpowers)
- Tiered memory with rollover (ai-agent-blueprint)
- Structured XML task definitions that are self-contained (get-shit-done)

### Simplicity Wins

The biggest performance gains in production systems came from **removing things** (complex tool definitions, RAG pipelines, routing logic), not adding them. A simpler context that fits well is better than a complex context that overwhelms.

---

## 5. Memory Architecture

### Three-Tier Persistence Model

The ai-agent-blueprint framework defines the most complete memory architecture:

**Tier 1: Active Memory** (2-3 days)
- Full detail on recent tasks, preferences, decisions
- Updated after every session
- Where active context lives
- Pruned weekly

**Tier 2: Weekly Memory** (7-10 days)
- Compressed summaries from active memory
- Key outcomes without implementation details
- Auto-rolled from Tier 1 based on age

**Tier 3: Index** (permanent)
- Keywords and pointers only
- "For X, see Y file or database"
- Manual updates for adding projects/people
- Never expires

### Rollover Process

1. Items >3 days old: Active → Weekly (compressed, preserving key decisions)
2. Items >10 days old: Weekly → Index (keywords and pointers only)
3. Full detail preserved where it matters; noise eliminated

### Memory Types

Four categories of memory serve different purposes:

| Type | What | Persistence |
|------|------|-------------|
| Short-term | Current context window | Session only |
| Episodic | Timestamped events and interactions | Days to weeks |
| Semantic | Structured facts and preferences | Weeks to permanent |
| Procedural | Workflows, skills, learned patterns | Permanent |

### Practical Memory Patterns

**File-based memory** (todo.md, progress.md, tasks.json) persisting across context resets is the simplest and most reliable approach.

**Git history as immutable memory**: Commits serve as the permanent record of what was done and why. Atomic commits with clear messages make git log a queryable knowledge base.

**Memory decay is essential**: Without it, systems grow unbounded and retrieval degrades. Use timestamps, weight recent memories higher, and implement eviction policies.

### What NOT to Store in Memory

- Code patterns and architecture (derivable from the code itself)
- Git history and recent changes (git log/blame are authoritative)
- Debugging solutions (the fix is in the code; the commit has the context)
- Anything in CLAUDE.md files (already loaded every session)
- Ephemeral task details (use todo lists instead)

---

## 6. Multi-Agent Orchestration

### Orchestration Patterns

Six distinct patterns emerged from the studied frameworks:

**1. Parallel Research**
- Spawn independent agents per topic
- All run simultaneously
- Aggregate results when complete
- Total time = slowest agent, not sum

**2. Sequential Pipeline**
- Each agent depends on previous output
- Agent 1 outputs → Agent 2 inputs
- Example: Research → Filter → Report

**3. Specialist Delegation**
- Different agents with different models for different expertise
- Cost optimization: Opus for analysis, Sonnet for execution, Haiku for verification
- Each specialist has domain-specific constraints

**4. Divide and Conquer**
- Split large task into independent subtasks
- Assign to parallel agents
- Merge results with conflict resolution

**5. Retry with Fallback**
- Primary agent attempts task
- On failure, fallback agent with different approach
- Escalate to human if both fail

**6. Background Processing**
- Long-running tasks delegated to background agents
- Main agent continues with other work
- Results collected when available

### Wave Execution

The get-shit-done framework's most powerful pattern:

```
WAVE 1 (parallel)    WAVE 2 (parallel)    WAVE 3
[Plan 01] [Plan 02]  [Plan 03] [Plan 04]  [Plan 05]
  User      Product      Orders     Cart      Checkout
  Model     Model        API        API       UI
```

- Independent plans → same wave → parallel execution
- Dependent plans → later wave → sequential
- Total time = longest dependency chain

**Design implication**: Vertical slices (feature end-to-end) parallelize better than horizontal layers (all models, then all APIs).

### Optimal Team Size

Research indicates **3-5 agents** with one reviewer-model agent per 3-4 builders. Beyond this, coordination overhead exceeds parallelization gains.

### Multi-Model Cost Profiles

| Profile | Planning | Execution | Verification |
|---------|----------|-----------|--------------|
| Quality | Opus | Opus | Sonnet |
| Balanced | Opus | Sonnet | Sonnet |
| Budget | Sonnet | Sonnet | Haiku |
| Inherit | Follow current setting | | |

### Why Multi-Agent Fails

- **Vague specs multiply errors** across parallel runs
- **Verification becomes the bottleneck** (generation outpaces review)
- **Machine-generated context files degrade performance** by ~3% (keep context human-authored or structured)

### The Stateless-but-Iterative Pattern

Reset each iteration to avoid accumulating confusion, but persist state through:
- Git history (commits as immutable record)
- Progress logs (todo.md, STATE.md)
- Task state files (structured per-phase artifacts)
- Configuration files (CLAUDE.md, AGENTS.md)

---

## 7. Workflow Design

### Staged Verification with Hard Gates

All studied frameworks enforce mandatory checkpoints between phases:

```
Brainstorm → [user approval] → Plan → [user review] →
Execute → [verification] → Review → [acceptance] → Ship
```

**Key insight**: Not all issues block progress. Use confidence gates:

| Confidence | Action |
|------------|--------|
| High | Block progress (exploitable vulnerabilities, logic errors) |
| Medium | Flag but don't block (performance concerns, maintainability) |
| Low | Advisory only (style preferences, minor improvements) |

### Atomic Task Decomposition

Every framework breaks work into small, independently meaningful pieces:

**Task granularity: 2-5 minutes each**
- "Write failing test" — one step
- "Run test to verify it fails" — one step
- "Implement minimal code" — one step
- "Run test to verify it passes" — one step
- "Commit" — one step

**Why this granularity works**:
- Each piece can be reviewed independently
- Failures are easy to bisect
- Progress is visible and measurable
- Reverts are clean and precise

### No-Placeholder Rule

Effective plans contain **zero placeholders**:
- No "TBD" or "TODO"
- No "add appropriate error handling" (show how)
- No "similar to Task N" (repeat the specifics)
- Every step contains the actual content an engineer needs

**Principle**: Assume the executor has zero context and questionable taste.

### Test-Driven Development Integration

The superpowers TDD skill enforces:

```
RED:     Write failing test
         → Verify it fails (correct reason, not typos)
GREEN:   Implement minimal code to pass
         → Verify it passes
REFACTOR: Clean up while staying green
         → Verify still passes
NEXT:    Repeat
```

**Iron law**: No production code without a failing test first. Violation = delete code, start over.

### Systematic Debugging

Four-phase investigation before any fix:

1. **Root Cause Investigation**: Read errors carefully, reproduce consistently, check recent changes
2. **Pattern Analysis**: Find working examples in same codebase, compare working vs broken
3. **Hypothesis and Testing**: Form single hypothesis with evidence, test scientifically
4. **Verification**: Fix at source (not symptom), verify consistently, check for regressions

**Anti-pattern**: Proposing fixes before understanding root cause.

### Spec-Driven Development

The get-shit-done framework structures every task as XML:

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>Use jose for JWT, validate credentials, return httpOnly cookie</action>
  <verify>curl -X POST returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

**Key elements**: Exact files, concrete actions, built-in verification, clear done criteria.

---

## 8. Hooks and Commands

### Hook Lifecycle Events

Claude Code hooks provide deterministic control at lifecycle events. Four hook types:

| Type | Description | Use Case |
|------|-------------|----------|
| Command | Shell script execution | Formatting, linting, file operations |
| HTTP | Endpoint calls | Notifications, external integrations |
| Prompt | Single-turn LLM judgment | Content review, classification |
| Agent | Multi-turn with tool access | Complex quality gates |

### Most Valuable Hook Patterns

**Auto-format on file change** (`PostToolUse` with Edit/Write matcher):
Run formatters automatically after every file edit, eliminating formatting discussions.

**Dangerous command blocking** (`PreToolUse`):
Block destructive commands (rm -rf, DROP TABLE, force push) before execution.

**Desktop notifications** (`Notification`/`Stop`):
Alert when long-running tasks complete.

**Context re-injection after compaction** (`SessionStart` with "compact" matcher):
Re-inject critical context when the conversation is compressed.

**Protected file blocking**:
Prevent edits to .env, lock files, .git/ contents.

**Quality gates on completion** (`Stop` with agent hook):
Run tests before allowing the agent to claim work is done.

**Environment reload** (`CwdChanged`):
Reload environment variables when changing directories (direnv integration).

### Exit Code Convention

- `0` = proceed normally
- `2` = block with feedback (hook rejected the action)
- Anything else = proceed with logging

### Configuration Cascade

Hook configurations cascade across scopes: user → project → local → managed policy → plugin → skill/agent. Later scopes can override earlier ones.

### Command Patterns

Commands are user-invocable entry points. Naming conventions observed:
- Prefixed by framework: `ce:brainstorm`, `gsd:plan-phase`
- Kebab-case: `new-project`, `verify-work`
- Clear verb-noun structure: `plan-phase`, `execute-phase`, `ship`

---

## 9. Code Review and Quality

### Multi-Persona Review

The compound-engineering framework's innovation: instead of one reviewer, spawn multiple specialized reviewers simultaneously:

| Category | Specialized Reviewers |
|----------|----------------------|
| Code Review | Architecture, API contracts, correctness, performance, security, reliability, testing, simplicity |
| Document Review | Coherence, design lens, feasibility, product lens, scope, security, adversarial |
| Research | Best practices, framework docs, git history, issue intelligence |

Each persona has specialized constraints and focus, catching issues a generalist would miss.

### Confidence-Calibrated Feedback

Review agents use confidence gates to avoid false positives:

- **High confidence** (block): Exploitable vulnerabilities, logic errors, test coverage gaps
- **Medium confidence** (flag): Performance issues, maintainability concerns
- **Low confidence** (advisory): Style preferences, minor improvements

This prevents review fatigue from low-value feedback blocking progress.

### Pre-Review Checklist

Before submitting for review, verify against the plan:
- **Coverage**: Does implementation match spec? Can you point to code for each requirement?
- **Correctness**: Logic sound? Edge cases handled? Error paths tested?
- **Quality**: Testable? Maintainable? Clear naming?

### Receiving Code Review

The superpowers framework emphasizes: don't blindly implement review suggestions. Instead:
- Verify feedback is technically sound
- Ask clarifying questions if unclear
- Push back on suggestions that introduce complexity without clear benefit
- Evidence-based responses, not performative agreement

---

## 10. Cross-Platform Compatibility

### Converter Architecture

The compound-engineering and get-shit-done frameworks support 8+ platforms through converter systems:

**Supported platforms**: Claude Code, Cursor, OpenCode, Codex, Copilot, Kiro, Windsurf, Qwen, Gemini CLI

### Authoring for Portability

Skills authored once should work across platforms. Key considerations:

- **Avoid platform-specific environment variables** in skill definitions
- **Use relative paths** for scripts and references
- **Include fallbacks** for platform-specific variables
- **Prefer native tools** (Glob, Grep, Read, Edit) over shell commands — these have equivalents across platforms
- **Use standard markdown** — avoid platform-specific syntax extensions

### Plugin Format

The compound-engineering framework uses a plugin directory structure:

```
.claude-plugin/     # Claude Code format
.cursor-plugin/     # Cursor format
.opencode/plugins/  # OpenCode format
.codex/             # Codex format
```

Each contains the same skills/agents/commands converted to the platform's expected format.

### Agent References

When referencing agents from skills in a multi-plugin environment, use **fully-qualified namespaces**:
- `compound-engineering:research:learnings-researcher` (works)
- `learnings-researcher` (fails at runtime due to ambiguity)

---

## 11. Self-Improvement and Learning

### Error Registry Pattern

Maintain a structured error log (`error-registry.json`):

```json
{
  "date": "2026-03-15",
  "severity": "high",
  "category": "deployment",
  "context": "Ran migration without backup",
  "workaround": "Restored from snapshot",
  "files": ["deploy.sh", "migration.sql"]
}
```

- Log failures that shouldn't recur
- Review weekly to identify root causes and patterns
- Prevents repeated debugging of the same issues

### Lessons System

Capture learned behaviors from corrections (`lessons.md`):

- **Date**: When learned
- **What went wrong**: The mistake or suboptimal approach
- **Correct approach**: What to do instead
- **Trigger conditions**: When this lesson applies
- **When first applied**: Validation that the lesson was used

Loaded at session start so patterns are reinforced. Built through consistent in-session logging.

### Self-Extension in Config

The most effective production configs include self-extension mechanisms directly in CLAUDE.md, not as a separate system. This means the global config itself instructs the agent on how to identify capability gaps, learn from corrections, and save preferences. When learning is a first-class concern of the config (not an afterthought in a separate lessons file), it happens more consistently.

### Session-End Protocol

At the end of each session:
1. Check for errors → log to error registry
2. Check for learnings → add to lessons system
3. Update memory with relevant context
4. Only effective if performed consistently

### Compound Engineering Philosophy

The compound-engineering framework's core thesis: **each unit of work should make the next unit easier**. This happens through:
- Skills that encode learned patterns
- Error registries that prevent repeated mistakes
- Lessons that improve future decisions
- Templates that standardize successful approaches

---

## 12. Key Principles

### 1. Structure Over Prompts

All systems provide structural context rather than relying on prompts alone: architectural constraints (CLAUDE.md), task decomposition (plans), skill libraries (reusable patterns), memory tiers (persistent context). Agents follow structure more reliably than vague guidance. Within that structure, principles generalize better than rules. "Prefer reversible actions" handles more situations than an enumerated list of dangerous commands. And every instruction should describe a concrete, observable behavior, not a quality aspiration. "Be thorough" means nothing; "before claiming completion, run it and show me output" is actionable.

### 2. Fresh Context Per Major Task

Context rot is inevitable. All production systems create clean contexts for execution: fresh 200k windows per plan, per-task subagents, sub-agents for parallel work. The main orchestrator stays lean while work happens in dedicated contexts.

### 3. Verification Before Claiming Success

Evidence before assertions. Always. Tests must pass before commit. Plans must be verified before execution. User acceptance testing before shipping. Root cause found before proposing fix.

### 4. Atomic, Reversible Decomposition

Break work into independently meaningful pieces (2-5 minute tasks). Each piece can be reviewed, debugged, and reverted cleanly. Atomic commits enable precise failure identification through bisection.

### 5. Staged Feedback with Human-in-the-Loop

Maintain explicit checkpoints: brainstorm → user approval → plan → user review → execute → verification → review → actionable feedback. This prevents rework and alignment issues. The user stays in control.

### 6. Context Engineering Over Capability Engineering

Rather than building new capabilities, focus on: what information does the agent need, when does it need it, and how should it be structured. Better context + existing capabilities consistently outperforms new capabilities + poor context.

### 7. Living Documentation

Skills, plans, and specs are executable context, not static reference. Documentation that the AI actually loads and follows is more likely to be followed than documentation written for humans. Design your documentation as agent input, not human reading material.

### 8. The Filesystem is the Database

Use files for state management, memory persistence, task tracking, and intermediate results. Files survive context resets, can be inspected by humans, work with git for versioning, and scale without infrastructure.

### 9. Simplicity is a Feature

The biggest performance gains in production systems came from removing things, not adding them. A simpler context that fits well beats a complex context that overwhelms. Start with the minimum viable structure and add complexity only when you have evidence it's needed.

### 10. Compound Over Linear

Design every tool, skill, and workflow so that using it once makes it better for next time. Error registries prevent repeated mistakes. Lessons improve future decisions. Templates standardize successful approaches. Each unit of work should make the next unit easier.

---

## Sources

### Example Projects Analyzed
- **ai-agent-blueprint**: Autonomous agent architecture with persistent memory
- **claude-md-template-pack**: Role-based CLAUDE.md templates
- **ai-playbook-ops**: Office automation workflows and prompt templates
- **compound-engineering-plugin**: Multi-agent engineering platform with 50+ skills
- **get-shit-done**: Spec-driven development with wave execution
- **superpowers**: Skills-first development workflow with hard gates

### Supplementary Research
- Anthropic documentation on Claude Code hooks, commands, and skills
- Context engineering research (Manus agent architecture, KV-cache optimization)
- Multi-agent orchestration patterns (OpenDev, ACM 2025 studies)
- AGENTS.md specification (Linux Foundation)
- "How I Structure CLAUDE.md After 1000+ Sessions" (Jock Samuels, 2025) — lean config, principles over rules, "Working With Me" pattern
