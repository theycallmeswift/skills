# Summarize Eval Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest eval suite for the summarize skill that verifies template structure, section compliance, input-type-specific formatting, and content quality using the existing test harness and assertion library.

**Architecture:** Follows the same pattern as the ghostwrite eval suite — session-scoped fixtures cache CLI outputs (one per input type), deterministic assertions check structure and hard limits, and the LLM judge handles semantic checks. Summarize-specific helpers live in `tests/skills/summarize/helpers.py`.

**Tech Stack:** Python 3.11+, pytest, pytest-xdist (all already installed)

---

## File Structure

```
tests/skills/summarize/
├── __init__.py
├── conftest.py                       # Source content fixtures + cached outputs (3 input types)
├── helpers.py                        # Summarize-specific parsing/assertion helpers
├── test_helpers.py                   # Unit tests for helpers (no CLI calls)
├── test_summarize_structure.py       # Template structure compliance (~8 tests)
└── test_summarize_input_types.py     # Input-type-specific formatting (~8 tests)
```

Also modified:
- `docs/evals.md` — add summarize to the test structure diagram

---

## Task 1: Summarize-Specific Helpers

**Files:**
- Create: `tests/skills/summarize/__init__.py`
- Create: `tests/skills/summarize/helpers.py`
- Test: `tests/skills/summarize/test_helpers.py`

These helpers parse the structured template output so individual tests can assert on specific sections without duplicating regex logic.

- [ ] **Step 1: Write the failing tests**

Create `tests/skills/summarize/test_helpers.py`:

````python
from textwrap import dedent

from tests.skills.summarize.helpers import (
    cliff_notes_bullets,
    comment_text,
    has_all_sections,
    h1_title,
    share_text,
    starts_with_h1,
    tldr_text,
    word_count,
)


class TestStartsWithH1:
    def test_starts_with_hash(self):
        assert starts_with_h1("# My Title\n\n## TL;DR\n...") is True

    def test_starts_with_preamble(self):
        assert starts_with_h1("Here's the summary:\n\n# My Title\n...") is False

    def test_empty_string(self):
        assert starts_with_h1("") is False


class TestH1Title:
    def test_extracts_plain_title(self):
        text = "# My Document Title\n\n## TL;DR\nSome text."
        assert h1_title(text) == "My Document Title"

    def test_extracts_link_title(self):
        text = "# [Article Title](https://example.com)\n\n## TL;DR\nSome text."
        assert h1_title(text) == "[Article Title](https://example.com)"

    def test_returns_none_when_missing(self):
        assert h1_title("No heading here.") is None


class TestHasAllSections:
    def test_all_present(self):
        text = dedent("""\
            # Title

            ## TL;DR

            Summary here.

            ## Cliff Notes

            - Point one

            ## Share

            ```
            Hot take here
            ```

            ## Comment

            ```
            My comment
            ```""")
        assert has_all_sections(text) == []

    def test_missing_sections(self):
        text = "# Title\n\n## TL;DR\n\nSummary."
        missing = has_all_sections(text)
        assert "## Cliff Notes" in missing
        assert "## Share" in missing
        assert "## Comment" in missing


class TestTldrText:
    def test_extracts_tldr(self):
        text = dedent("""\
            # Title

            ## TL;DR

            This is the summary.

            ## Cliff Notes

            - Point one""")
        assert tldr_text(text) == "This is the summary."

    def test_returns_none_when_missing(self):
        assert tldr_text("# Title\n\n## Cliff Notes\n\n- One") is None


class TestCliffNotesBullets:
    def test_counts_bullets(self):
        text = dedent("""\
            # Title

            ## TL;DR

            Summary.

            ## Cliff Notes

            - First point
            - Second point
            - Third point

            ## Share

            ```
            Hot take
            ```""")
        bullets = cliff_notes_bullets(text)
        assert len(bullets) == 3

    def test_returns_empty_when_missing(self):
        assert cliff_notes_bullets("# Title\n\n## TL;DR\nText.") == []


class TestShareText:
    def test_extracts_share_content(self):
        text = dedent("""\
            ## Share

            ```
            This is the hot take
            https://example.com
            ```

            ## Comment""")
        assert "This is the hot take" in share_text(text)

    def test_returns_none_when_missing(self):
        assert share_text("# Title\n\n## TL;DR\nText.") is None


class TestCommentText:
    def test_extracts_comment_content(self):
        text = dedent("""\
            ## Comment

            ```
            Great take, but shipping matters more than architecture.
            ```""")
        assert "shipping matters more" in comment_text(text)

    def test_returns_none_when_missing(self):
        assert comment_text("# Title\n\n## TL;DR\nText.") is None


class TestWordCount:
    def test_counts_words(self):
        assert word_count("Hello world, this is a test.") == 6

    def test_empty_string(self):
        assert word_count("") == 0
````

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/skills/summarize/test_helpers.py -v -n0
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.skills.summarize'`

- [ ] **Step 3: Create package files and implement helpers**

Create `tests/skills/summarize/__init__.py` (empty file).

Create `tests/skills/summarize/helpers.py`:

````python
"""Summarize-specific test helpers. Parse the structured template output."""

import re


REQUIRED_SECTIONS = ["## TL;DR", "## Cliff Notes", "## Share", "## Comment"]


def starts_with_h1(text: str) -> bool:
    """Check that the output starts with '# ' (no preamble)."""
    return text.startswith("# ")


def h1_title(text: str) -> str | None:
    """Extract the H1 title text (everything after '# ' on the first line)."""
    match = re.match(r"^# (.+)", text)
    return match.group(1).strip() if match else None


def has_all_sections(text: str) -> list[str]:
    """Return list of required section headings missing from text. Empty = pass."""
    return [section for section in REQUIRED_SECTIONS if section not in text]


def _extract_section(text: str, heading: str, next_headings: list[str]) -> str | None:
    """Extract text between a heading and the next heading (or end of string)."""
    pattern = re.escape(heading) + r"\s*\n(.*?)(?="
    if next_headings:
        pattern += "|".join(re.escape(h) for h in next_headings)
    pattern += r"|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def tldr_text(text: str) -> str | None:
    """Extract the TL;DR paragraph text."""
    return _extract_section(text, "## TL;DR", ["## Cliff Notes", "## Share", "## Comment"])


def cliff_notes_bullets(text: str) -> list[str]:
    """Extract Cliff Notes bullets as a list of strings."""
    section = _extract_section(text, "## Cliff Notes", ["## Share", "## Comment"])
    if not section:
        return []
    return [line.strip() for line in section.splitlines() if re.match(r"^\s*-\s", line)]


def share_text(text: str) -> str | None:
    """Extract the content inside the Share code fence."""
    section = _extract_section(text, "## Share", ["## Comment"])
    if not section:
        return None
    fence_match = re.search(r"```\s*\n(.*?)\n\s*```", section, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else None


def comment_text(text: str) -> str | None:
    """Extract the content inside the Comment code fence."""
    section = _extract_section(text, "## Comment", [])
    if not section:
        return None
    fence_match = re.search(r"```\s*\n(.*?)\n\s*```", section, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else None


def word_count(text: str) -> int:
    """Return total word count."""
    return len(text.split()) if text else 0
````

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/skills/summarize/test_helpers.py -v -n0
```

Expected: all 16 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/skills/summarize/__init__.py tests/skills/summarize/helpers.py tests/skills/summarize/test_helpers.py
git commit -m "feat: add summarize test helpers with unit tests"
```

---

## Task 2: Summarize Fixtures

**Files:**
- Create: `tests/skills/summarize/conftest.py`

Three input types to test: URL, file, and pasted text. Each gets a source fixture, a prompt fixture, and a cached output fixture (one CLI call each, cached for the session).

The URL input type requires a real URL to fetch via brightdata MCP. We use a stable, well-known page. The file input type needs a local file created in the test working directory. The pasted text input is just raw text in the prompt.

- [ ] **Step 1: Write the failing test**

Create `tests/skills/summarize/test_fixtures.py`:

```python
def test_url_source_fixture(url_source):
    assert url_source.startswith("http")


def test_url_prompt_fixture(url_prompt):
    assert "summarize" in url_prompt.lower()
    assert "http" in url_prompt


def test_pasted_source_fixture(pasted_source):
    assert len(pasted_source) > 100


def test_pasted_prompt_fixture(pasted_prompt):
    assert "summarize" in pasted_prompt.lower()


def test_file_prompt_fixture(file_prompt):
    assert "summarize" in file_prompt.lower()
    assert ".txt" in file_prompt or ".md" in file_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/skills/summarize/test_fixtures.py -v -n0
```

Expected: FAIL — `fixture 'url_source' not found`

- [ ] **Step 3: Create conftest.py with summarize fixtures**

Create `tests/skills/summarize/conftest.py`:

```python
from textwrap import dedent

import pytest


# --- Source content per input type ---


@pytest.fixture(scope="session")
def url_source():
    return "https://github.blog/engineering/the-technology-behind-github-models/"


@pytest.fixture(scope="session")
def pasted_source():
    return dedent("""\
        The landscape of developer education is changing rapidly. Traditional
        computer science programs are struggling to keep pace with industry demands,
        and students are increasingly turning to hands-on learning experiences to
        build the skills employers actually want. At Major League Hacking (MLH),
        we've seen this firsthand through our hackathon community, which now reaches
        1 in 3 CS students globally.

        Over the past year, we've supported 500,000 developers across 1,500 events
        in 65 countries. But the numbers only tell part of the story. What really
        matters is the transformation we see in participants. Students who attend
        their first hackathon often describe it as a turning point, the moment they
        went from studying code to shipping products.

        Our fellowship program has been another proof point. We've placed 200
        early-career developers at companies like GitHub, Meta, and Shopify, with
        a 95% satisfaction rate from both fellows and host companies. The common
        thread? Learning by doing beats learning by reading every time.

        If you're a student wondering whether to attend a hackathon, or an employer
        considering hands-on hiring, the data speaks for itself. Check out
        https://mlh.io/impact for the full report.""")


@pytest.fixture(scope="session")
def file_source():
    return dedent("""\
        # Hackathon Organizer Guide

        Running a successful hackathon requires careful planning across several
        key areas: venue logistics, sponsor management, mentorship coordination,
        and participant experience.

        ## Venue and Logistics

        Book your venue at least 3 months in advance. You need reliable WiFi
        that can handle 500+ simultaneous connections, enough power outlets for
        every table, and a layout that encourages collaboration. Budget $15-25
        per participant for food across the full 24-36 hour event.

        ## Sponsorship

        Start outreach 4-6 months before the event. Companies typically commit
        $5,000-$25,000 for hackathon sponsorships. Offer API credits, mentors,
        and branded challenges as activation options beyond just logo placement.

        ## Mentorship

        Recruit 1 mentor per 10 participants. Brief them on common issues:
        environment setup, API authentication, and deployment. The best mentors
        ask questions rather than writing code for teams.

        ## Judging

        Use a rubric with 4 categories: technical complexity, design, impact,
        and presentation. Give judges 3 minutes per demo with 1 minute for Q&A.
        Calibrate scoring with a practice round before demos begin.""")


# --- Prompts per input type ---


@pytest.fixture(scope="session")
def url_prompt(url_source):
    return f"Summarize this: {url_source}"


@pytest.fixture(scope="session")
def pasted_prompt(pasted_source):
    return f"Summarize this:\n\n{pasted_source}"


@pytest.fixture(scope="session")
def file_prompt(runner, file_source):
    """Write source to a .md file in the runner's cwd, then ask to summarize it."""
    file_path = runner.cwd / "hackathon-guide.md"
    file_path.write_text(file_source)
    return f"Summarize this file: {file_path}"


# --- Cached outputs (one CLI call per input type) ---


@pytest.fixture(scope="session")
def url_output(runner, url_prompt):
    return runner.run(url_prompt)


@pytest.fixture(scope="session")
def pasted_output(runner, pasted_prompt):
    return runner.run(pasted_prompt)


@pytest.fixture(scope="session")
def file_output(runner, file_prompt):
    return runner.run(file_prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/skills/summarize/test_fixtures.py -v -n0
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Delete fixture test file and commit**

Remove `tests/skills/summarize/test_fixtures.py`.

```bash
git add tests/skills/summarize/conftest.py
git commit -m "feat: add summarize test fixtures with source content per input type"
```

---

## Task 3: Template Structure Tests (test_summarize_structure.py)

**Files:**
- Create: `tests/skills/summarize/test_summarize_structure.py`

These tests verify rules that apply to ALL summarize outputs regardless of input type. They use the pasted-text output as the primary test subject since it's the simplest (no URL fetch, no file I/O).

- [ ] **Step 1: Write the tests**

Create `tests/skills/summarize/test_summarize_structure.py`:

```python
from tests.skills.summarize.helpers import (
    cliff_notes_bullets,
    comment_text,
    has_all_sections,
    share_text,
    starts_with_h1,
    word_count,
)
from tests.support.assertions import (
    banned_words,
    no_em_dashes,
)


class TestSummarizeStructure:
    """Template structure compliance. Every summarize output must pass these."""

    def test_starts_with_h1(self, pasted_output):
        assert starts_with_h1(pasted_output), (
            f"Output must start with '# '. First 80 chars: {pasted_output[:80]}"
        )

    def test_has_all_sections(self, pasted_output):
        missing = has_all_sections(pasted_output)
        assert missing == [], f"Missing required sections: {missing}"

    def test_cliff_notes_max_8_bullets(self, pasted_output):
        bullets = cliff_notes_bullets(pasted_output)
        assert 1 <= len(bullets) <= 8, (
            f"Cliff Notes has {len(bullets)} bullets (expected 1-8)"
        )

    def test_share_is_1_to_2_sentences(self, pasted_output):
        share = share_text(pasted_output)
        assert share is not None, "Share section is missing or has no code fence"
        # Count sentences by splitting on sentence-ending punctuation
        import re
        sentences = [s.strip() for s in re.split(r'[.!?]+', share) if s.strip()]
        # Filter out bare URLs which aren't sentences
        sentences = [s for s in sentences if not s.startswith("http")]
        assert 1 <= len(sentences) <= 2, (
            f"Share has {len(sentences)} sentences (expected 1-2): {share}"
        )

    def test_comment_max_20_words(self, pasted_output):
        comment = comment_text(pasted_output)
        assert comment is not None, "Comment section is missing or has no code fence"
        count = word_count(comment)
        assert count <= 20, f"Comment is {count} words (max 20): {comment}"

    def test_no_em_dashes(self, pasted_output):
        violations = no_em_dashes(pasted_output)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_no_banned_words(self, pasted_output):
        violations = banned_words(pasted_output)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_preamble_or_postscript(self, pasted_output):
        lines = pasted_output.strip().splitlines()
        first_line = lines[0].strip()
        assert first_line.startswith("# "), (
            f"Preamble detected before H1. First line: {first_line}"
        )
        last_line = lines[-1].strip()
        preamble_phrases = [
            "let me know",
            "here's the summary",
            "hope this helps",
            "feel free to",
        ]
        for phrase in preamble_phrases:
            assert phrase not in last_line.lower(), (
                f"Postscript detected: {last_line}"
            )
```

- [ ] **Step 2: Run tests to verify they execute**

Run:
```bash
uv run pytest tests/skills/summarize/test_summarize_structure.py -v -n0
```

Expected: Tests execute using the cached `pasted_output` fixture (one CLI call). Results depend on model output quality — the point is to verify the test infrastructure works.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/test_summarize_structure.py
git commit -m "feat: add summarize template structure tests"
```

---

## Task 4: Input Type Tests (test_summarize_input_types.py)

**Files:**
- Create: `tests/skills/summarize/test_summarize_input_types.py`

These tests verify formatting rules that differ by input type: H1 link format, URL presence/absence in Share fence.

- [ ] **Step 1: Write the tests**

Create `tests/skills/summarize/test_summarize_input_types.py`:

```python
import re

from tests.skills.summarize.helpers import (
    h1_title,
    has_all_sections,
    share_text,
    starts_with_h1,
)


class TestUrlInput:
    """URL input: H1 is a markdown link, Share fence ends with bare URL."""

    def test_starts_with_h1(self, url_output):
        assert starts_with_h1(url_output), (
            f"URL output must start with '# '. First 80 chars: {url_output[:80]}"
        )

    def test_has_all_sections(self, url_output):
        missing = has_all_sections(url_output)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_markdown_link(self, url_output):
        title = h1_title(url_output)
        assert title is not None, "H1 title is missing"
        assert re.match(r"\[.+\]\(https?://.+\)", title), (
            f"URL input H1 should be a markdown link [Title](url). Got: {title}"
        )

    def test_share_contains_url(self, url_output, url_source):
        share = share_text(url_output)
        assert share is not None, "Share section is missing or has no code fence"
        assert "http" in share, (
            f"URL input Share fence should contain the source URL. Share: {share}"
        )


class TestPastedInput:
    """Pasted text input: H1 is plain text (no link), Share has no URL."""

    def test_h1_is_plain_text(self, pasted_output):
        title = h1_title(pasted_output)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"Pasted input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, pasted_output):
        share = share_text(pasted_output)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"Pasted input Share fence should NOT contain a URL. Share: {share}"
        )


class TestFileInput:
    """File input: H1 is plain text (no link), Share has no URL."""

    def test_starts_with_h1(self, file_output):
        assert starts_with_h1(file_output), (
            f"File output must start with '# '. First 80 chars: {file_output[:80]}"
        )

    def test_has_all_sections(self, file_output):
        missing = has_all_sections(file_output)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_plain_text(self, file_output):
        title = h1_title(file_output)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"File input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, file_output):
        share = share_text(file_output)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"File input Share fence should NOT contain a URL. Share: {share}"
        )
```

- [ ] **Step 2: Run tests to verify they execute**

Run:
```bash
uv run pytest tests/skills/summarize/test_summarize_input_types.py -v -n0
```

Expected: Tests execute using cached output fixtures (one CLI call per input type, 3 total). Results depend on model output quality.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/test_summarize_input_types.py
git commit -m "feat: add summarize input type formatting tests"
```

---

## Task 5: Documentation Update

**Files:**
- Modify: `docs/evals.md`

- [ ] **Step 1: Update the test structure diagram in docs/evals.md**

In `docs/evals.md`, find the test structure tree and add the summarize directory. Change:

```
└── skills/
    └── ghostwrite/
        ├── conftest.py                      # Source content + cached output fixtures
        ├── helpers.py                       # Ghostwrite-specific helpers (signoff, hashtags)
        ├── test_helpers.py                  # Helper unit tests
        ├── test_ghostwrite_rules.py         # Rule compliance (~6 tests)
        └── test_ghostwrite_mediums.py       # Medium formatting (~10 tests)
```

To:

```
└── skills/
    ├── ghostwrite/
    │   ├── conftest.py                      # Source content + cached output fixtures
    │   ├── helpers.py                       # Ghostwrite-specific helpers (signoff, hashtags)
    │   ├── test_helpers.py                  # Helper unit tests
    │   ├── test_ghostwrite_rules.py         # Rule compliance (~6 tests)
    │   └── test_ghostwrite_mediums.py       # Medium formatting (~10 tests)
    └── summarize/
        ├── conftest.py                      # Source content + cached output fixtures (3 input types)
        ├── helpers.py                       # Summarize-specific helpers (template parsing)
        ├── test_helpers.py                  # Helper unit tests
        ├── test_summarize_structure.py      # Template structure compliance (~8 tests)
        └── test_summarize_input_types.py    # Input-type formatting (~8 tests)
```

- [ ] **Step 2: Commit**

```bash
git add docs/evals.md
git commit -m "docs: add summarize to test structure in evals guide"
```

---

## Task 6: Full Suite Verification

- [ ] **Step 1: Run the full suite with make test**

Run:
```bash
make test
```

Expected: ~32 tests execute in parallel (16 existing ghostwrite + harness tests, 16 new summarize tests). Helper unit tests should all pass. Integration tests depend on model output quality.

- [ ] **Step 2: Run lint to confirm code quality**

Run:
```bash
make lint && make format
```

Expected: No errors, no formatting changes (or auto-fixed).

- [ ] **Step 3: Fix any lint issues and commit**

If lint or format made changes:

```bash
git add -u
git commit -m "style: fix lint and formatting"
```

- [ ] **Step 4: Final verification — verify clean state**

Run:
```bash
git status
```

Expected: clean working tree, all changes committed.
