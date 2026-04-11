from tests.support.assertions import (
    banned_words,
    long_sentences,
    no_em_dashes,
    stats_preserved,
    urls_preserved,
)


class TestGhostwriteRules:
    """General rule compliance tests. Each test uses cached output from a single CLI call."""

    def test_no_em_dashes(self, email_output):
        violations = no_em_dashes(email_output.text)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_sentences_under_25_words(self, email_output):
        violations = long_sentences(email_output.text)
        assert violations == [], f"Sentences over 25 words: {violations}"

    def test_no_banned_words(self, email_output):
        violations = banned_words(email_output.text)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_ai_tells(self, linkedin_output):
        violations = banned_words(linkedin_output.text)
        assert violations == [], f"AI tells found: {violations}"

    def test_urls_preserved(self, email_output, email_source):
        missing = urls_preserved(email_source, email_output.text)
        assert missing == [], f"URLs missing from output: {missing}"

    def test_stats_preserved(self, email_output, email_source):
        missing = stats_preserved(email_source, email_output.text)
        assert missing == [], f"Stats missing from output: {missing}"
