# Shared Assertions + Summarize Adversarial Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a `shared_assertions` mechanism in eval JSON files so the summarize suite stops duplicating its ~10 structural assertions across four cases, then add three adversarial cases that exercise failure modes summarize currently has zero coverage for.

**Architecture:** Extend the eval file schema with an optional top-level `shared_assertions` array. At load time, `discovery.load_eval_file` merges each case's assertions with the shared list (shared first, per-case second) before constructing the `EvalCase`. Cases that don't need the shared set can opt out with `"use_shared_assertions": false`. After the refactor lands, add three new summarize cases covering paste-raw-text, short-input-no-padding, and ambiguous-reference.

**Tech Stack:** Python 3.12+, pytest, JSON.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items I3, C4.

**Depends on:** Plan 02 (deterministic assertions) should land first — summarize's shared assertions include tool-trace entries that benefit from deterministic grading.

---

## Context the implementer needs

- Eval files are loaded by `load_eval_file` in `tests/support/harness/discovery.py`. Today the function reads `data["name"]` and `data["evals"]` — anything at the top level other than those keys is silently ignored.
- Each `EvalCase` has an `assertions: list[dict]` field. Shared assertions need to be injected there before construction.
- Summarize (`tests/skills/summarize/evals.json`) has 4 cases. Three are web scraping (`devto-top-article`, `devto-rust-tab-orchestrator`, `anthropic-claude-character`) with identical format assertions. `local-pdf` has the same format assertions plus a different tool-trace set. After plan 02 lands, the tool-trace entries are deterministic.
- The format assertions we'll extract: H1 title, clickable link near title, `## TL;DR` section, TL;DR is plain body not heading/bold, `## Cliff Notes` section, Cliff Notes is a bulleted list 5–8 items, `## Share` section, Share section has a code fence with a bare URL, `## Comment` section, Comment section is a code fence ≤20 words.

---

## Task 1: Add `shared_assertions` support to discovery

**Files:**
- Modify: `tests/support/harness/discovery.py`
- Test: `tests/support/harness/test_discovery.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/support/harness/test_discovery.py`:

```python
def test_shared_assertions_are_prepended_to_each_case(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "shared_assertions": [
            {"text": "Output is non-empty"},
            {"text": "Output has a heading"},
        ],
        "evals": [
            {
                "id": "c1",
                "turns": ["hi"],
                "assertions": [{"text": "Output mentions cats"}],
            },
            {
                "id": "c2",
                "turns": ["hi"],
                "assertions": [{"text": "Output mentions dogs"}],
            },
        ],
    }))
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == [
        "Output is non-empty",
        "Output has a heading",
        "Output mentions cats",
    ]
    assert [a["text"] for a in suite.cases[1].assertions] == [
        "Output is non-empty",
        "Output has a heading",
        "Output mentions dogs",
    ]


def test_case_can_opt_out_of_shared_assertions(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "shared_assertions": [{"text": "shared one"}],
        "evals": [
            {
                "id": "opted-out",
                "turns": ["hi"],
                "use_shared_assertions": False,
                "assertions": [{"text": "own one"}],
            },
        ],
    }))
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == ["own one"]


def test_no_shared_assertions_key_works_as_before(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "evals": [
            {"id": "c1", "turns": ["hi"], "assertions": [{"text": "only"}]},
        ],
    }))
    suite = load_eval_file(f, kind="skill")
    assert [a["text"] for a in suite.cases[0].assertions] == ["only"]
```

- [ ] **Step 2: Run them, verify they fail**

Run: `uv run pytest tests/support/harness/test_discovery.py -k shared -v`
Expected: FAIL — the first test will fail because `c1.assertions` only contains `[{"text": "Output mentions cats"}]`.

- [ ] **Step 3: Implement merging in `load_eval_file`**

Modify `load_eval_file` in `tests/support/harness/discovery.py` to read `shared_assertions` and merge:

```python
def load_eval_file(path: Path, kind: EvalKind) -> EvalSuite:
    data = json.loads(path.read_text())
    shared = data.get("shared_assertions", [])
    if not isinstance(shared, list):
        raise ValueError(
            f"{path}: 'shared_assertions' must be a list of assertion dicts."
        )

    cases: list[EvalCase] = []
    for c in data["evals"]:
        own = c.get("assertions", [])
        if c.get("use_shared_assertions", True):
            merged = [*shared, *own]
        else:
            merged = list(own)
        cases.append(EvalCase(
            id=str(c["id"]),
            turns=_load_turns(c, path),
            files=c.get("files", []),
            assertions=merged,
            grader_model=c.get("grader_model"),
            cleanup=_validate_cleanup(c.get("cleanup", []), path),
        ))

    return EvalSuite(
        name=data["name"],
        kind=kind,
        source_path=path,
        cases=cases,
    )
```

(If plan 01 has not yet landed, replace `_validate_cleanup(c.get("cleanup", []), path)` with `c.get("cleanup", [])`.)

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/discovery.py tests/support/harness/test_discovery.py
git commit -m "feat(harness): support shared_assertions in eval files"
```

---

## Task 2: Migrate summarize to shared_assertions

**Files:**
- Modify: `tests/skills/summarize/evals.json`

The shared block covers the 10 format assertions every case needs. Per-case assertions hold only what differs: the tool-trace checks (different between web and PDF cases) and a case-specific content check (e.g. "H1 uses the doc title" for the PDF case).

- [ ] **Step 1: Rewrite the file**

Replace the full contents of `tests/skills/summarize/evals.json` with:

```json
{
  "name": "summarize",
  "shared_assertions": [
    {"text": "Output contains an H1 title (line starting with '# ')"},
    {"text": "Output contains a '## TL;DR' section"},
    {"text": "TL;DR is 1-2 sentences of plain body text, not rendered as a heading or bold block"},
    {"text": "Output contains a '## Cliff Notes' section"},
    {"text": "Cliff Notes contains a bulleted list with 5-8 items"},
    {"text": "Output contains a '## Share' section"},
    {"text": "Share section contains a code fence with a bare URL on its own line"},
    {"text": "Output contains a '## Comment' section"},
    {"text": "Comment section contains a code fence with content of 20 words or fewer"}
  ],
  "evals": [
    {
      "id": "devto-top-article",
      "turns": [
        "Summarize the top article on dev.to that isn't a challenge or contest announcement"
      ],
      "files": [],
      "assertions": [
        {"text": "Output contains a clickable link to the source URL near the title"},
        {"tool_called": "scrape_as_markdown"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
      ]
    },
    {
      "id": "devto-rust-tab-orchestrator",
      "turns": [
        "Summarize this article: https://dev.to/tasenikol/when-chrome-ate-my-ram-designing-a-pressure-aware-tab-orchestrator-with-rust-1g05"
      ],
      "files": [],
      "assertions": [
        {"text": "Output contains a clickable link to the source URL near the title"},
        {"tool_called": "scrape_as_markdown"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
      ]
    },
    {
      "id": "anthropic-claude-character",
      "turns": [
        "Summarize this page for me https://www.anthropic.com/research/claude-character"
      ],
      "files": [],
      "assertions": [
        {"text": "Output contains a clickable link to the source URL near the title"},
        {"tool_called": "scrape_as_markdown"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
      ]
    },
    {
      "id": "local-pdf",
      "turns": [
        "Summarize this PDF: test-paper.pdf"
      ],
      "files": ["test-paper.pdf"],
      "assertions": [
        {"text": "H1 title uses the document/paper title or filename, not a URL"},
        {"tool_called": "Read"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"},
        {"tool_not_called": "brightdata"}
      ]
    }
  ]
}
```

- [ ] **Step 2: Verify the suite still loads and assertion counts look right**

Run:
```bash
uv run python -c "
from pathlib import Path
from tests.support.harness.discovery import load_eval_file
s = load_eval_file(Path('tests/skills/summarize/evals.json'), kind='skill')
for c in s.cases:
    print(c.id, len(c.assertions))
"
```
Expected output:
```
devto-top-article 13
devto-rust-tab-orchestrator 13
anthropic-claude-character 13
local-pdf 14
```
(9 shared + 4 or 5 case-specific.)

- [ ] **Step 3: Smoke-run the suite**

Run: `uv run python -m tests.support.harness summarize --no-baseline`
Expected: all four cases run; grading.json for each has the shared 9 assertions followed by case-specific ones.

- [ ] **Step 4: Commit**

```bash
git add tests/skills/summarize/evals.json
git commit -m "refactor(summarize): extract format checks to shared_assertions"
```

---

## Task 3: Add `paste-raw-text` adversarial case

**Files:**
- Modify: `tests/skills/summarize/evals.json`

User pastes the body of an article directly — no URL. The skill should summarize the pasted text *without* calling any scraping tool.

- [ ] **Step 1: Append the case**

Add to the `evals` array in `tests/skills/summarize/evals.json`, after `local-pdf`:

```json
    {
      "id": "paste-raw-text",
      "turns": [
        "Summarize this for me:\n\nThe rise of the pull request has fundamentally reshaped how software teams collaborate. Originally introduced by GitHub in 2008 as a lightweight way to propose changes across forks, the pull request has evolved into the primary unit of code review, discussion, and integration in modern engineering workflows. Teams argue about PR size, PR templates, PR etiquette, and how long a PR can sit in review before it becomes stale. Companies have built entire product lines around PR automation — linters that comment inline, bots that auto-assign reviewers based on CODEOWNERS, dashboards that show how long each PR spent waiting at each stage.\n\nBut the pull request has a dark side. Large PRs are where bugs hide, because reviewers skim when they should read. Small PRs fragment context, forcing reviewers to hold a mental model across six tabs. Teams that merge PRs too fast ship bugs; teams that merge too slow ship nothing. The median PR in a busy repository sits in review for two days, and those two days are where velocity goes to die. Solving the pull request problem has become a cottage industry: trunk-based development advocates, stacked diff tools like Graphite, and AI review bots all claim to have the answer.\n\nThe real answer is probably boring: small, focused changes; reviewers who actually read; and a team culture that treats a pending PR as a shared problem, not one person's backlog item."
      ],
      "files": [],
      "assertions": [
        {"text": "H1 title is based on the pasted content (e.g. about pull requests or code review), not a generic placeholder"},
        {"text": "Cliff Notes bullets reflect the pasted text (PR size, review time, trunk-based, etc.), not invented topics"},
        {"tool_not_called": "scrape_as_markdown"},
        {"tool_not_called": "scrape_batch"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
      ]
    }
```

- [ ] **Step 2: Run the case**

Run: `uv run python -m tests.support.harness summarize --no-baseline`
Expected: `paste-raw-text` completes; grading.json shows the tool_not_called entries PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/evals.json
git commit -m "test(summarize): add paste-raw-text adversarial case"
```

---

## Task 4: Add `short-input-no-padding` adversarial case

**Files:**
- Modify: `tests/skills/summarize/evals.json`

User pastes a 4-sentence note. The skill should produce a short summary that doesn't invent Cliff Notes bullets ungrounded in the source. Because the shared `Cliff Notes contains a bulleted list with 5-8 items` assertion would force padding here, this case opts out of shared assertions and supplies its own minimal format checks.

- [ ] **Step 1: Append the case**

Add to the `evals` array:

```json
    {
      "id": "short-input-no-padding",
      "turns": [
        "Summarize this note:\n\nWe decided to push the Q3 demo day to the week of September 15. The reason is that the new partner onboarding flow won't be ready in time for the original date. Marketing has been told. Calendar invites will go out Friday."
      ],
      "files": [],
      "use_shared_assertions": false,
      "assertions": [
        {"text": "Output contains an H1 title (line starting with '# ')"},
        {"text": "Output contains a '## TL;DR' section"},
        {"text": "TL;DR correctly names the Q3 demo day date change as the core fact"},
        {"text": "Every Cliff Notes bullet is directly supported by the 4-sentence input (mentions demo day, Sept 15, partner onboarding, marketing, or calendar invites — not invented details)"},
        {"text": "Output does NOT pad the Cliff Notes with generic project-management commentary not present in the input"},
        {"tool_not_called": "scrape_as_markdown"},
        {"tool_not_called": "WebFetch"}
      ]
    }
```

- [ ] **Step 2: Run the case**

Run: `uv run python -m tests.support.harness summarize --no-baseline`
Expected: `short-input-no-padding` completes; grading.json has exactly 7 expectations (no shared set applied).

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/evals.json
git commit -m "test(summarize): add short-input-no-padding adversarial case"
```

---

## Task 5: Add `ambiguous-reference` adversarial case

**Files:**
- Modify: `tests/skills/summarize/evals.json`

User asks to summarize "that thing" with no link and no pasted content. The skill should ask for clarification instead of scraping something arbitrary.

- [ ] **Step 1: Append the case**

Add to the `evals` array:

```json
    {
      "id": "ambiguous-reference",
      "turns": [
        "summarize that thing I sent you yesterday"
      ],
      "files": [],
      "use_shared_assertions": false,
      "assertions": [
        {"text": "Output asks the user to clarify what 'that thing' refers to (link, paste, filename, etc.)"},
        {"text": "Output does NOT invent or guess an article, URL, or document to summarize"},
        {"text": "Output does NOT produce the standard H1/TL;DR/Cliff Notes format — it is a clarifying question, not a summary"},
        {"tool_not_called": "scrape_as_markdown"},
        {"tool_not_called": "scrape_batch"},
        {"tool_not_called": "WebFetch"},
        {"tool_not_called": "WebSearch"}
      ]
    }
```

- [ ] **Step 2: Run the full summarize suite**

Run: `uv run python -m tests.support.harness summarize --no-baseline`
Expected: 7 cases total (4 original + 3 new), all run to completion. Deterministic tool_not_called entries grade in-process.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/evals.json
git commit -m "test(summarize): add ambiguous-reference adversarial case"
```

---

## Verification

- [ ] `uv run pytest tests/support -v` — all green
- [ ] `uv run python -m tests.support.harness summarize --no-baseline` — 7 cases run, grading.json shows shared-then-own assertion ordering for cases that opt in
- [ ] Spot-check a summarize grading.json: deterministic entries interleave correctly
- [ ] Inspect `ambiguous-reference/with_skill/outputs/output.md`: agent asks for clarification, no scraping tools fired (check tool_trace in artifacts)

## Out of scope for this plan

- Content gaps in ghostwrite/prompt-engineer/scope (plan 04)
- Splitting the github-webhook-slack scope case (plan 05)
- Grader truncation (plan 05)
