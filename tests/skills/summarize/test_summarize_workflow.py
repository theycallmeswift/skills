import re

import pytest

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


@pytest.fixture(params=["pasted_output", "url_output", "file_output"])
def summarize_output(request):
    """Parametrize workflow tests across all three input types."""
    return request.getfixturevalue(request.param)


class TestSummarizeStructure:
    """Template structure compliance. Every summarize output must pass these."""

    def test_starts_with_h1(self, summarize_output):
        assert starts_with_h1(summarize_output.final_output), (
            f"Output must start with '# '. First 80 chars: {summarize_output.final_output[:80]}"
        )

    def test_has_all_sections(self, summarize_output):
        missing = has_all_sections(summarize_output.final_output)
        assert missing == [], f"Missing required sections: {missing}"

    def test_cliff_notes_max_8_bullets(self, summarize_output):
        bullets = cliff_notes_bullets(summarize_output.final_output)
        assert 1 <= len(bullets) <= 8, f"Cliff Notes has {len(bullets)} bullets (expected 1-8)"

    def test_share_is_1_to_2_sentences(self, summarize_output):
        share = share_text(summarize_output.final_output)
        assert share is not None, "Share section is missing or has no code fence"
        # Strip bare URL lines before counting sentences
        lines = [line for line in share.splitlines() if not line.strip().startswith("http")]
        prose = " ".join(lines)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if s.strip()]
        assert 1 <= len(sentences) <= 2, (
            f"Share has {len(sentences)} sentences (expected 1-2): {share}"
        )

    def test_comment_max_20_words(self, summarize_output):
        comment = comment_text(summarize_output.final_output)
        assert comment is not None, "Comment section is missing or has no code fence"
        count = word_count(comment)
        assert count <= 20, f"Comment is {count} words (max 20): {comment}"

    def test_no_em_dashes(self, summarize_output):
        violations = no_em_dashes(summarize_output.final_output)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_no_banned_words(self, summarize_output):
        violations = banned_words(summarize_output.final_output)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_preamble_or_postscript(self, summarize_output):
        lines = summarize_output.final_output.strip().splitlines()
        first_line = lines[0].strip()
        assert first_line.startswith("# "), f"Preamble detected before H1. First line: {first_line}"
        last_line = lines[-1].strip()
        postscript_phrases = [
            "let me know",
            "here's the summary",
            "hope this helps",
            "feel free to",
        ]
        for phrase in postscript_phrases:
            assert phrase not in last_line.lower(), f"Postscript detected: {last_line}"


class TestSummarizeProcess:
    """Verify the summarize skill follows its prescribed process."""

    def test_dispatches_ghostwrite_subagent(self, summarize_output):
        agent_calls = [
            c for c in summarize_output.tool_calls if c["name"] == "Agent"
        ]
        ghostwrite_calls = [
            c for c in agent_calls
            if "ghostwrite" in c["input"].get("prompt", "").lower()
        ]
        assert len(ghostwrite_calls) >= 1, (
            f"Expected summarize to dispatch a ghostwrite subagent. "
            f"Agent calls found: {[c['input'].get('description', '') for c in agent_calls]}"
        )

    def test_invokes_summarize_skill(self, summarize_output):
        skill_calls = [
            c for c in summarize_output.tool_calls if c["name"] == "Skill"
        ]
        summarize_calls = [
            c for c in skill_calls
            if "summarize" in c["input"].get("skill", "").lower()
        ]
        assert len(summarize_calls) >= 1, (
            f"Expected Skill tool to load summarize. "
            f"Skill calls found: {[c['input'].get('skill', '') for c in skill_calls]}"
        )

    def test_url_input_fetches_via_mcp(self, url_output):
        tool_names = [c["name"] for c in url_output.tool_calls]
        assert "mcp__brightdata__scrape_as_markdown" in tool_names, (
            f"URL input should fetch via scrape_as_markdown. "
            f"Tool calls: {tool_names}"
        )

    def test_file_input_uses_read(self, file_output):
        read_calls = [c for c in file_output.tool_calls if c["name"] == "Read"]
        assert len(read_calls) >= 1, (
            f"File input should use Read tool to fetch source. "
            f"Tool calls: {[c['name'] for c in file_output.tool_calls]}"
        )

    def test_pasted_input_skips_fetch(self, pasted_output):
        fetch_tools = {"Read", "mcp__brightdata__scrape_as_markdown"}
        fetch_calls = [
            c for c in pasted_output.tool_calls if c["name"] in fetch_tools
        ]
        assert fetch_calls == [], (
            f"Pasted input should not fetch via Read or scrape_as_markdown. "
            f"Unexpected calls: {[c['name'] for c in fetch_calls]}"
        )
