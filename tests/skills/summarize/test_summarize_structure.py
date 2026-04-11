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
    """Parametrize structure tests across all three input types."""
    return request.getfixturevalue(request.param)


class TestSummarizeStructure:
    """Template structure compliance. Every summarize output must pass these."""

    def test_starts_with_h1(self, summarize_output):
        assert starts_with_h1(summarize_output.text), (
            f"Output must start with '# '. First 80 chars: {summarize_output.text[:80]}"
        )

    def test_has_all_sections(self, summarize_output):
        missing = has_all_sections(summarize_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_cliff_notes_max_8_bullets(self, summarize_output):
        bullets = cliff_notes_bullets(summarize_output.text)
        assert 1 <= len(bullets) <= 8, f"Cliff Notes has {len(bullets)} bullets (expected 1-8)"

    def test_share_is_1_to_2_sentences(self, summarize_output):
        share = share_text(summarize_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        # Strip bare URL lines before counting sentences
        lines = [line for line in share.splitlines() if not line.strip().startswith("http")]
        prose = " ".join(lines)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if s.strip()]
        assert 1 <= len(sentences) <= 2, (
            f"Share has {len(sentences)} sentences (expected 1-2): {share}"
        )

    def test_comment_max_20_words(self, summarize_output):
        comment = comment_text(summarize_output.text)
        assert comment is not None, "Comment section is missing or has no code fence"
        count = word_count(comment)
        assert count <= 20, f"Comment is {count} words (max 20): {comment}"

    def test_no_em_dashes(self, summarize_output):
        violations = no_em_dashes(summarize_output.text)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_no_banned_words(self, summarize_output):
        violations = banned_words(summarize_output.text)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_preamble_or_postscript(self, summarize_output):
        lines = summarize_output.text.strip().splitlines()
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
