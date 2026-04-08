# Deterministic Tool-Trace Assertions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic assertion types that grade tool-trace facts in Python instead of the LLM judge, then migrate existing TOOL TRACE / Skill-tool assertions to them.

**Architecture:** Extend the assertion schema from a plain `{"text": str}` dict to support typed entries: `{"tool_called": "<name>"}`, `{"tool_not_called": "<name>"}`, `{"skill_invoked": "<name>"}`. The grader partitions assertions — deterministic ones are evaluated in Python against `run.tool_trace`, text ones continue to the LLM. Results merge into a single `Grading` object preserving order.

**Tech Stack:** Python 3.12+, pytest.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items I5, I1, C5.

**Depends on:** Plan 01 (harness safety) should land first so the orchestrator is clean.

---

## Context the implementer needs

- Each entry in `run.tool_trace` looks like `{"name": str, "input": dict, "turn": int}` (see `tests/support/harness/runner.py` around line 123).
- The plugin's Skill tool shows up as `name == "Skill"` with `input.skill` holding the skill identifier (e.g. `"mechaswift:ghostwrite"` or `"ghostwrite"`). Match both prefixed and bare forms.
- Brightdata MCP tools have names like `mcp__brightdata__scrape_as_markdown`. "Contains" matching is good enough here — downstream the grader only needs substring match.
- Today assertions flow through `grader.grade()` → LLM as `{"text": ...}` dicts. The LLM is told about a "TOOL TRACE" section. We are adding a parallel code path that never sees the LLM.
- Existing assertion text — e.g. `"TOOL TRACE does NOT show any call to \`WebFetch\` or \`WebSearch\`"` — will be replaced by deterministic entries. Keep assertion ordering stable so the grading.json output reads the same.
- Current call sites of deterministic-worthy assertions:
  - `tests/core/skill-triggers.json` — 4 cases, each with `"The Skill tool was invoked with a skill name matching 'X'"`.
  - `tests/skills/summarize/evals.json` — 4 cases, each asserts brightdata was called and WebFetch/WebSearch was not (the `local-pdf` case flips this).
  - `tests/core/no-ai-attribution.json` — `"No gh pr create ... was actually executed"` (C5 — rework to use `tool_not_called`).

---

## Task 1: Add deterministic assertion types to the grader

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/test_grader.py`

- [ ] **Step 1: Write failing tests for the deterministic grader helper**

Add to `tests/support/harness/test_grader.py` (create module-level imports as needed):

```python
from tests.support.harness.grader import _grade_deterministic
from tests.support.harness.runner import RunResult


def _run_with_trace(trace):
    return RunResult(
        stdout="", files_written={}, input_tokens=0, output_tokens=0,
        duration_s=0.0, exit_code=0, tool_trace=trace, turn_count=1,
    )


def test_tool_called_passes_when_name_matches_substring():
    run = _run_with_trace([{"name": "mcp__brightdata__scrape_as_markdown", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "scrape_as_markdown"}], run)
    assert exps == [{
        "text": "tool_called: scrape_as_markdown",
        "passed": True,
        "evidence": "matched tool 'mcp__brightdata__scrape_as_markdown' on turn 1",
    }]


def test_tool_called_fails_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "no matching tool" in exps[0]["evidence"].lower()


def test_tool_not_called_passes_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is True


def test_tool_not_called_fails_when_present():
    run = _run_with_trace([{"name": "WebFetch", "input": {"url": "x"}, "turn": 2}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "turn 2" in exps[0]["evidence"]


def test_skill_invoked_matches_bare_name():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_matches_prefixed_name():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_fails_when_different_skill():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "summarize"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False


def test_skill_invoked_fails_when_no_skill_tool_at_all():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "no Skill tool" in exps[0]["evidence"]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/support/harness/test_grader.py -k deterministic -v`
Expected: all fail with `ImportError` (the helper doesn't exist yet).

- [ ] **Step 3: Implement `_grade_deterministic` in grader.py**

Add to `tests/support/harness/grader.py` above the `grade` function:

```python
def _match_tool(trace: list[dict], needle: str) -> dict | None:
    """Return the first trace entry whose name contains `needle`, else None."""
    for entry in trace:
        if needle in entry.get("name", ""):
            return entry
    return None


def _match_skill_invocation(trace: list[dict], skill: str) -> dict | None:
    """Return the first Skill tool entry whose input.skill matches.

    Accepts both bare ('ghostwrite') and prefixed ('mechaswift:ghostwrite') forms.
    """
    for entry in trace:
        if entry.get("name") != "Skill":
            continue
        inv = entry.get("input", {}).get("skill", "")
        if inv == skill or inv.endswith(f":{skill}"):
            return entry
    return None


def _grade_deterministic(assertions: list[dict], run: "RunResult") -> list[dict]:
    """Evaluate deterministic assertions against the tool trace.

    Returns one expectation dict per input assertion, in order. Non-deterministic
    assertions (those with a 'text' key) are returned as None placeholders so the
    caller can slot them back in after the LLM judge runs.
    """
    out: list[dict | None] = []
    for a in assertions:
        if "tool_called" in a:
            needle = a["tool_called"]
            hit = _match_tool(run.tool_trace, needle)
            if hit is not None:
                out.append({
                    "text": f"tool_called: {needle}",
                    "passed": True,
                    "evidence": f"matched tool '{hit['name']}' on turn {hit.get('turn', '?')}",
                })
            else:
                out.append({
                    "text": f"tool_called: {needle}",
                    "passed": False,
                    "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
                })
        elif "tool_not_called" in a:
            needle = a["tool_not_called"]
            hit = _match_tool(run.tool_trace, needle)
            if hit is None:
                out.append({
                    "text": f"tool_not_called: {needle}",
                    "passed": True,
                    "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
                })
            else:
                out.append({
                    "text": f"tool_not_called: {needle}",
                    "passed": False,
                    "evidence": f"found '{hit['name']}' on turn {hit.get('turn', '?')}",
                })
        elif "skill_invoked" in a:
            skill = a["skill_invoked"]
            hit = _match_skill_invocation(run.tool_trace, skill)
            if hit is not None:
                out.append({
                    "text": f"skill_invoked: {skill}",
                    "passed": True,
                    "evidence": f"Skill tool fired with skill='{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
                })
            else:
                has_any_skill = any(e.get("name") == "Skill" for e in run.tool_trace)
                if has_any_skill:
                    fired = [e.get("input", {}).get("skill", "?") for e in run.tool_trace if e.get("name") == "Skill"]
                    evidence = f"Skill tool fired but with different skills: {fired}"
                else:
                    evidence = "no Skill tool invocations in trace"
                out.append({
                    "text": f"skill_invoked: {skill}",
                    "passed": False,
                    "evidence": evidence,
                })
        else:
            out.append(None)
    return [e for e in out if e is not None]
```

- [ ] **Step 4: Run the deterministic tests**

Run: `uv run pytest tests/support/harness/test_grader.py -k deterministic -v`
Expected: 8/8 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/test_grader.py
git commit -m "feat(harness): add deterministic tool-trace assertion types"
```

---

## Task 2: Wire deterministic assertions into the `grade` pipeline

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/test_grader.py`

We want `grade()` to:
1. Split assertions into deterministic (has `tool_called`/`tool_not_called`/`skill_invoked`) vs text-based (has `text`).
2. Run deterministic ones through `_grade_deterministic`.
3. Run text-based ones through the LLM (as today).
4. Merge results in **original order** so the grading.json output reads top-to-bottom matching the eval JSON.

- [ ] **Step 1: Write the failing integration test**

Add to `test_grader.py`:

```python
import asyncio
from unittest.mock import patch

from tests.support.harness.grader import grade
from tests.support.harness.models import Grading


def test_grade_merges_deterministic_and_text_in_order(monkeypatch):
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1},
    ])
    assertions = [
        {"text": "output is a rewrite"},
        {"skill_invoked": "ghostwrite"},
        {"text": "tone is friendly"},
    ]

    async def fake_llm_grade(run_, text_assertions, model, original_prompt):
        # Simulate LLM grading only the text entries it received, in order.
        return [
            {"text": a["text"], "passed": True, "evidence": "ok"}
            for a in text_assertions
        ]

    monkeypatch.setattr("tests.support.harness.grader._grade_text_llm", fake_llm_grade)

    result: Grading = asyncio.run(grade(run, assertions))
    assert [e["text"] for e in result.expectations] == [
        "output is a rewrite",
        "skill_invoked: ghostwrite",
        "tone is friendly",
    ]
    assert all(e["passed"] for e in result.expectations)
    assert result.passed == 3
    assert result.total == 3
```

- [ ] **Step 2: Run it, verify it fails**

Run: `uv run pytest tests/support/harness/test_grader.py::test_grade_merges_deterministic_and_text_in_order -v`
Expected: FAIL (no `_grade_text_llm` helper, merge logic missing).

- [ ] **Step 3: Refactor `grade` to split and merge**

Rewrite the `grade` function in `tests/support/harness/grader.py`. Extract the existing LLM call into a new `_grade_text_llm` helper:

```python
_DETERMINISTIC_KEYS = ("tool_called", "tool_not_called", "skill_invoked")


def _is_deterministic(assertion: dict) -> bool:
    return any(k in assertion for k in _DETERMINISTIC_KEYS)


async def _grade_text_llm(
    run: RunResult,
    assertions: list[dict],
    model: str | None,
    original_prompt: str,
) -> list[dict]:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

    if not assertions:
        return []

    options = ClaudeAgentOptions(
        model=model or DEFAULT_GRADER_MODEL,
        output_format=_OUTPUT_SCHEMA,
    )
    prompt = _build_prompt(run, assertions, original_prompt)

    structured: dict | None = None
    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            elif getattr(message, "result", None):
                parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    parts.append(block.text)

    if structured is not None:
        return structured["expectations"]

    raw = "".join(parts).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")
    if not raw:
        raise RuntimeError("grader returned empty response")
    data = json.loads(raw)
    return data["expectations"]


async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str | None = None,
    original_prompt: str = "",
) -> Grading:
    if not assertions:
        return Grading.from_expectations([])

    # Evaluate deterministic entries in-process; queue text entries for the LLM.
    text_assertions = [a for a in assertions if not _is_deterministic(a)]
    llm_expectations = await _grade_text_llm(run, text_assertions, model, original_prompt)

    # Merge back in original order.
    llm_iter = iter(llm_expectations)
    merged: list[dict] = []
    for a in assertions:
        if _is_deterministic(a):
            merged.extend(_grade_deterministic([a], run))
        else:
            merged.append(next(llm_iter))

    return Grading.from_expectations(merged)
```

Delete the old body of `grade()` that lives below the assertions split (the original top-to-bottom LLM flow). Keep `DEFAULT_GRADER_MODEL`, `GRADER_PROMPT`, `_OUTPUT_SCHEMA`, and `_build_prompt` unchanged.

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/support/harness/test_grader.py::test_grade_merges_deterministic_and_text_in_order -v`
Expected: PASS.

- [ ] **Step 5: Run the full grader test suite**

Run: `uv run pytest tests/support/harness/test_grader.py -v`
Expected: all PASS (pre-existing tests may need to import the new helper but should otherwise be unaffected).

- [ ] **Step 6: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/test_grader.py
git commit -m "feat(harness): split grading into deterministic and LLM paths"
```

---

## Task 3: Migrate `skill-triggers` core eval to `skill_invoked`

**Files:**
- Modify: `tests/core/skill-triggers.json`

- [ ] **Step 1: Rewrite all four cases**

Replace the full contents of `tests/core/skill-triggers.json` with:

```json
{
  "name": "skill-triggers",
  "evals": [
    {
      "id": "ghostwrite-on-rewrite-request",
      "turns": [
        "Rewrite this in my voice as a Slack message to the team:\n\nHey everyone, I wanted to share some quick thoughts on where we are heading into Q2. The Hackathon Season numbers came in stronger than we expected, with attendance up 18% year over year and sponsor renewal sitting at 94%. That gives us real room to invest in the new Fellowship cohort without stretching the team. I want us to spend this week locking the cohort timeline and then move fast on outreach. Let me know if anything is blocking you and we will sort it out in standup tomorrow."
      ],
      "files": [],
      "assertions": [
        {"skill_invoked": "ghostwrite"},
        {"text": "The output is a rewritten version of the input, not a refusal or clarifying question"}
      ]
    },
    {
      "id": "scope-on-design-request",
      "turns": [
        "help me scope a new feature where users can schedule recurring exports of their data"
      ],
      "files": [],
      "assertions": [
        {"skill_invoked": "scope"},
        {"text": "The response engages with scoping the idea (asking clarifying questions or proposing approaches), not jumping to implementation"}
      ]
    },
    {
      "id": "summarize-on-tldr-request",
      "turns": [
        "tl;dr this for me: https://www.anthropic.com/news/claude-4"
      ],
      "files": [],
      "assertions": [
        {"skill_invoked": "summarize"}
      ]
    },
    {
      "id": "prompt-engineer-on-prompt-request",
      "turns": [
        "write me a prompt for an LLM that extracts structured JSON from invoices"
      ],
      "files": [],
      "assertions": [
        {"skill_invoked": "prompt-engineer"},
        {"text": "The response produces or asks clarifying questions to produce a structured prompt, not a generic answer"}
      ]
    }
  ]
}
```

- [ ] **Step 2: Smoke-run the migrated suite**

Run: `uv run python -m tests.support.harness skill-triggers`
Expected: each case's `skill_invoked:` assertion is graded deterministically (evidence mentions "Skill tool fired with skill=…"). If a case fails, inspect the `tool_trace` in the artifact dir to confirm whether the model actually fired the Skill tool or not — a legit model miss is a finding, not a plan bug.

- [ ] **Step 3: Commit**

```bash
git add tests/core/skill-triggers.json
git commit -m "test(skill-triggers): use deterministic skill_invoked assertions"
```

---

## Task 4: Migrate `summarize` TOOL TRACE assertions to deterministic types

**Files:**
- Modify: `tests/skills/summarize/evals.json`

Replace every `"TOOL TRACE shows the brightdata MCP was used…"` with `{"tool_called": "scrape_as_markdown"}` and every `"TOOL TRACE does NOT show any call to \`WebFetch\` or \`WebSearch\`"` with two entries: `{"tool_not_called": "WebFetch"}`, `{"tool_not_called": "WebSearch"}`. For the `local-pdf` case: replace the brightdata assertion with `{"tool_called": "Read"}` (input will need `test-paper.pdf` — but `tool_called` only checks the tool name, so substring `"Read"` matches), and the negative assertion with three `tool_not_called` entries for `WebFetch`, `WebSearch`, `brightdata`.

**Note:** `"Read"` substring-matches `"Read"` tool calls. It would also match a hypothetical `"ReadRemote"` if that existed — it doesn't, but if the harness adds tools later this could drift. For this plan, substring is acceptable; strict equality can be a follow-up.

- [ ] **Step 1: Edit `tests/skills/summarize/evals.json`**

For each of the three web-scraping cases (`devto-top-article`, `devto-rust-tab-orchestrator`, `anthropic-claude-character`), replace the last two assertions (the TOOL TRACE pair) with:

```json
        {"tool_called": "scrape_as_markdown"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
```

For the `local-pdf` case, replace the last two assertions with:

```json
        {"tool_called": "Read"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"},
        {"tool_not_called": "brightdata"}
```

- [ ] **Step 2: Smoke-run summarize**

Run: `uv run python -m tests.support.harness summarize --no-baseline`
Expected: the deterministic entries are graded without an LLM call; text assertions still go to the LLM. Artifact grading.json should show evidence strings like "matched tool 'mcp__brightdata__scrape_as_markdown' on turn 1".

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/evals.json
git commit -m "test(summarize): use deterministic tool_called assertions"
```

---

## Task 5: Rework `no-ai-attribution/pr-draft` to drop the tautology

**Files:**
- Modify: `tests/core/no-ai-attribution.json`

Per C5, the current `pr-draft` case tells the model "Do not run gh" and then asserts gh was not run. That is circular. Two fixes:

1. Drop the `"No gh pr create … was actually executed"` assertion (the prompt itself enforces it, it adds no signal).
2. Add a third adversarial case `amend-existing-attribution` where the agent is asked to rewrite a commit whose message *already* contains a `Co-Authored-By` trailer, and grading asserts the rewrite strips it.

- [ ] **Step 1: Edit `pr-draft` to remove the tautological assertion**

In `tests/core/no-ai-attribution.json`, delete the last assertion from `pr-draft`:

```json
        {
          "text": "No `gh pr create` (or equivalent push/PR command) was actually executed"
        }
```

Replace it with a deterministic `tool_not_called` entry that actually checks the tool trace (which is non-tautological — it verifies no Bash tool call contained `gh pr create`). Since `tool_not_called` matches on the *tool name* and not the input, and `gh` runs via `Bash`, the cleaner move is to leave the assertion deleted. Do that: delete the line and leave `pr-draft` with 6 assertions.

- [ ] **Step 2: Add the `amend-existing-attribution` case**

Append to the `evals` array in `tests/core/no-ai-attribution.json`:

```json
    {
      "id": "amend-existing-attribution",
      "turns": [
        "In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, and create README.md with the text 'hello'. Stage it and commit it with this exact commit message (use a HEREDOC so the trailer is preserved):\n\n    initial commit\n\n    Co-Authored-By: Claude <noreply@anthropic.com>\n\nThen amend that commit (using `git commit --amend`) so the final commit message has a cleaner one-line summary and no trailers. Show `git log -1 --format=full` when you are done."
      ],
      "files": [],
      "assertions": [
        {"text": "A fake-repo directory was created and a real commit exists at HEAD"},
        {"text": "The final commit message has NO `Co-Authored-By:` trailer"},
        {"text": "The final commit message names no AI model, vendor, or harness (Claude, Anthropic, GPT, etc.)"},
        {"text": "The final commit message does not contain 'noreply@anthropic.com' or any anthropic.com link"},
        {"text": "The final commit message has a concise one-line summary (not the original 'initial commit' with the trailer appended)"}
      ]
    }
```

- [ ] **Step 3: Smoke-run the core eval**

Run: `uv run python -m tests.support.harness no-ai-attribution`
Expected: three cases run. `pr-draft` has 6 assertions now. `amend-existing-attribution` runs to completion — if the model preserves the trailer during amend, that is a legitimate finding and the case should FAIL loudly (that is the point of the test).

- [ ] **Step 4: Commit**

```bash
git add tests/core/no-ai-attribution.json
git commit -m "test(no-ai-attribution): drop tautology, add amend-trailer case"
```

---

## Verification

- [ ] `uv run pytest tests/support -v` — all green (includes new grader tests)
- [ ] `uv run python -m tests.support.harness skill-triggers` — deterministic assertions grade without LLM for Skill tool checks
- [ ] `uv run python -m tests.support.harness summarize --no-baseline` — tool-trace entries show "matched tool …" evidence
- [ ] `uv run python -m tests.support.harness no-ai-attribution` — three cases present, amend case runs
- [ ] Inspect a `grading.json` for a summarize case: confirm deterministic entries have `text` fields like `"tool_called: scrape_as_markdown"` interleaved correctly with LLM-graded text assertions.

## Out of scope for this plan

- Shared assertion sets (plan 03)
- Summarize content additions (plan 03)
- Scope/ghostwrite/prompt-engineer content gaps (plan 04)
- Grader truncation (plan 05)
