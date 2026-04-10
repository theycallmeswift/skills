import re

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
