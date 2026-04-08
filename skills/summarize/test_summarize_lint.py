"""Unit tests for skills/summarize/lint.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "summarize_lint_under_test", Path(__file__).parent / "lint.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
lint = _mod.lint

GOOD = """\
# [Some Great Article](https://example.com/post)

## TL;DR

The article argues that small focused pull requests beat large ones for code review velocity and correctness.

## Cliff Notes

- **Median PR** sits in review for two days on busy repos.
- Large PRs hide bugs because reviewers skim.
- Small PRs fragment context across many tabs.
- Trunk-based advocates, stacked diffs, and AI bots all compete.
- The real fix is small focused changes and a team culture of shared ownership.

## Share

```
Small PRs, fast reviews, shared culture. That is the whole answer.
https://example.com/post
```

## Comment

```
Two-day median review time is where velocity goes to die.
```
"""

# Known-bad: local-pdf — agent narration prefix, no title, no summary, no bullets
BAD_LOCAL_PDF = """\
Now I have the full paper content. Let me draft the summary components and invoke ghostwrite for the Share and Comment sections.

**My drafts:**
- **Share takeaway**: DeepSeek proved you don't have to choose between quality and cost, MLA + MoE delivers top-tier open-source performance.
- **Comment angle**: The MLA result is striking.SHARE

DeepSeek-V2 is a good reminder that quality and efficiency aren't a tradeoff.

COMMENT

93% KV cache reduction while beating MHA on benchmarks.
"""

# Known-bad: devto-top-article — narration, no title, no bullets, no summary para
BAD_DEVTO = """\
The top non-challenge article by reactions is **"Top 7 Featured DEV Posts of the Week"** with 53 reactions. Let me fetch the full article.Now let me call ghostwrite for the Share and Comment sections.Share:

this week's dev top 7 is genuinely unhinged in the best way.

Comment:

212 reactions for "the browser already solved it."
"""


def _rule_names(findings: list[str]) -> set[str]:
    return {f.split(":")[1].strip() for f in findings}


def test_good_output_lints_clean():
    assert lint(GOOD) == []


def test_bad_local_pdf_catches_narration_and_structure():
    findings = lint(BAD_LOCAL_PDF)
    rules = _rule_names(findings)
    assert "no_narration_prefix" in rules
    # Also missing proper title / summary / bullets
    assert "title" in rules or "summary_paragraph" in rules or "bullet_count" in rules


def test_bad_devto_catches_narration():
    findings = lint(BAD_DEVTO)
    rules = _rule_names(findings)
    assert "no_narration_prefix" in rules


def test_em_dash_is_rejected():
    text = GOOD.replace("Two-day median review time", "Two-day median — review time")
    findings = lint(text)
    assert "no_em_dash" in _rule_names(findings)


def test_bullet_count_three_bullets_is_fine():
    # Short input: 3 bullets is legitimate; floor removed.
    text = """\
# Title

Short summary paragraph here.

- one
- two
- three

## Share

```
share
```

## Comment

```
comment
```
"""
    assert "bullet_count" not in _rule_names(lint(text))


def test_bullet_count_over_ceiling_fails():
    bullets = "\n".join(f"- b{i}" for i in range(10))
    text = f"""\
# Title

Summary paragraph.

{bullets}

## Share

```
share
```

## Comment

```
comment
```
"""
    assert "bullet_count" in _rule_names(lint(text))


def test_bullet_count_no_list_fails():
    text = """\
# Title

Summary paragraph only. No list.

## Share

```
share
```

## Comment

```
comment
```
"""
    assert "bullet_count" in _rule_names(lint(text))


def test_comment_too_long():
    long_comment = " ".join(["word"] * 25)
    text = f"""\
# Title

Short summary paragraph.

- a
- b
- c
- d
- e

## Share

```
share line
```

## Comment

```
{long_comment}
```
"""
    findings = lint(text)
    assert "comment_block" in _rule_names(findings)


def test_cli_entry(tmp_path: Path):
    import subprocess
    import sys

    good = tmp_path / "good.md"
    good.write_text(GOOD)
    r = subprocess.run(
        [sys.executable, "skills/summarize/lint.py", str(good)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout

    bad = tmp_path / "bad.md"
    bad.write_text(BAD_LOCAL_PDF)
    r = subprocess.run(
        [sys.executable, "skills/summarize/lint.py", str(bad)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "FAIL" in r.stdout
