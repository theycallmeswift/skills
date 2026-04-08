# Skill self-lint

## Context

The eval harness overhaul surfaced a real summarize bug: on `devto-top-article` and `local-pdf`, the agent emitted only the Share/Comment ghostwrite blocks with no title, no summary, no bulleted key points. Other runs leaked agent narration ("Now I have the full paper content. Let me draft...") or em dashes into the final output. These are structural rule violations, not taste calls — exactly the class of bug a deterministic linter catches cheaply and reliably.

Today we rely on the LLM grader to catch these via prose assertions like "Output contains a bulleted list of 5-8 key points." That works, but it's flaky (grader variance), slow (one LLM call per run), and only catches failures after the fact. A lint script the skill runs before finalizing would turn the same bugs into self-correcting retries.

## Goal

Give skills a deterministic self-check they can run on their draft output before presenting it to the user, and let evals reuse the same lint as a deterministic assertion.

## Scope

- `summarize` — primary target. Covers the bugs we just saw.
- `ghostwrite` — reuse the em-dash check (absolute rule in SKILL.md, still leaks).
- Eval harness — new assertion type `{"lint": "<skill>"}` that runs the same script against the captured output.

Out of scope: `scope`, `prompt-engineer` (no fixed output format to lint).

## Design

### Lint scripts

Each skill that has deterministic format rules ships a `lint.py` next to its `SKILL.md`:

```
skills/summarize/lint.py
skills/ghostwrite/lint.py
```

Contract:
- Reads the draft from a file path passed as argv[1] (not stdin — we want the eval harness and the agent to both call it the same way).
- Prints findings to stdout, one per line, in the form `FAIL: <rule>: <evidence>`.
- Exit 0 = clean. Exit 1 = findings. No other exit codes.
- No dependencies beyond the stdlib. These run inside the agent's tool loop and inside the harness; both need to be fast and hermetic.

Shared rules go in `skills/_lint/` as importable helpers so ghostwrite's em-dash check and summarize's em-dash check are the same code:

```
skills/_lint/__init__.py
skills/_lint/rules.py          # no_em_dash, has_title, bullet_count_in_range, ...
```

### summarize/lint.py rules

1. First non-empty line is a title (H1 `# ...`, bold `**...**`, or a short line followed by a blank line — not a sentence ending in a period).
2. Between the title and the first list, there is at least one non-list paragraph (the summary). 1–2 sentences. This catches the truncation bug where the agent jumps straight to Share/Comment.
3. There is a bulleted list with 5–8 items somewhere in the body.
4. There is a "Share" block — heading, code fence, blockquote, or labeled block containing the word "Share" or clearly delimited shareable text. (Loose match; the shared assertion already allows multiple forms.)
5. There is a "Comment" block, distinct from Share, ≤20 words.
6. No em dashes (—) anywhere in the output.
7. No agent narration prefix. Reject outputs whose first 200 chars contain any of: "Let me", "Now I", "I'll draft", "I have the", "Here's the summary" followed by a colon and newline. (Tight allowlist — we want to catch the leak, not reject legitimate prose.)

Rule 7 is the one that would have caught `local-pdf`.

### ghostwrite/lint.py rules

1. No em dashes.
2. No banned phrases (import the existing banlist from `skills/ghostwrite/references/banned-phrases.md` if it exists; otherwise inline the list).
3. No AI attribution strings ("Generated with", "Co-Authored-By: Claude", etc.) — duplicates the no-ai-attribution hook but catches it at skill level too.

### SKILL.md changes

Add a final step to each skill's checklist:

> Before presenting the output, write your draft to `tmp/<skill>-draft.md`, run `python skills/<skill>/lint.py tmp/<skill>-draft.md`, and fix any findings. Only present once the lint is clean.

`tmp/` is already gitignored and used for scratch.

### Eval harness integration

New deterministic assertion type alongside `tool_called` / `skill_invoked`:

```json
{"lint": "summarize"}
```

Graded in Python (no LLM call). The harness writes the captured `output.md` to a temp file, runs `python skills/<name>/lint.py <path>`, and reports exit code + stdout as assertion evidence. Implementation lives in `tests/support/harness/assertions.py` (or wherever deterministic assertions currently live — check `grader.py` / `runner.py`).

Once `{"lint": "summarize"}` exists, the summarize suite can drop the prose versions of the structural assertions (title, summary, bullet count, em dash) and keep LLM grading for content-grounding and voice. Cheaper, faster, less flaky.

## Tasks

1. Create `skills/_lint/rules.py` with `no_em_dash`, `has_title`, `bullet_count_in_range`, `has_labeled_block`, `word_count_at_most`, `no_narration_prefix` helpers. Unit tests in `skills/_lint/test_rules.py`.
2. Create `skills/summarize/lint.py` calling the shared helpers. Unit tests in `skills/summarize/test_lint.py` — pass each of the known-bad outputs from `tmp/evals/2026-04-08T04-26-10/summarize/` and assert the lint catches them; pass a known-good output and assert clean.
3. Create `skills/ghostwrite/lint.py` with the em dash + banned-phrases + AI attribution rules. Unit tests against the `devto-top-article` Share-block em-dash failure from the Opus run.
4. Update `skills/summarize/SKILL.md` and `skills/ghostwrite/SKILL.md` with the self-check step.
5. Add `{"lint": "<skill>"}` assertion support to the harness. Unit test with a fixture skill and a captured output.
6. Update `docs/evals.md` "Assertion types" section with the new `lint` form.
7. Rewrite `tests/skills/summarize/evals.json`: replace the structural shared assertions with a single `{"lint": "summarize"}`. Keep the content/grounding prose assertions.
8. Rewrite `tests/skills/ghostwrite/evals.json` the same way — `{"lint": "ghostwrite"}` plus content assertions.
9. Rerun the full suite on both Opus and Haiku. Confirm the previously-flaky failures (devto-top-article, local-pdf, devto-rust-tab-orchestrator) are now either clean or fail deterministically on the lint with useful evidence.

## Verification

- `uv run pytest skills/_lint skills/summarize skills/ghostwrite` — all green.
- `make test ARGS="summarize ghostwrite"` on Opus — lint-based cases should be as reliable as the old deterministic tool-call assertions.
- `make test ARGS="--model claude-haiku-4-5-20251001 summarize ghostwrite"` — the self-check in SKILL.md should let Haiku recover from its own structural mistakes, visible as higher with-skill pass rates.
- Spot-check one `tmp/evals/.../with_skill/outputs/output.md` per case to confirm the lint ran in the agent's loop (tool trace should show the `Bash` call to `python skills/summarize/lint.py`).

## Out of scope

- Linting `scope` or `prompt-engineer` outputs (no fixed format to lint).
- Auto-fixing lint failures in-script. The agent reads the findings and rewrites; the lint never mutates the draft.
- Hooking the lint into a pre-commit or CI step outside the eval harness.
