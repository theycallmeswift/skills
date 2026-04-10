from tests.support.assertions import (
    banned_words,
    long_sentences,
    no_em_dashes,
    stats_preserved,
    urls_preserved,
)


class TestGhostwriteRules:
    """General rule compliance tests. Each test rewrites email source and checks one rule."""

    def test_no_em_dashes(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = no_em_dashes(output)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_sentences_under_25_words(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = long_sentences(output)
        assert violations == [], f"Sentences over 25 words: {violations}"

    def test_no_banned_words(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = banned_words(output)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_ai_tells(self, runner, linkedin_prompt):
        output = runner.run(linkedin_prompt)
        violations = banned_words(output)
        assert violations == [], f"AI tells found: {violations}"

    def test_urls_preserved(self, runner, email_prompt, email_source):
        output = runner.run(email_prompt)
        missing = urls_preserved(email_source, output)
        assert missing == [], f"URLs missing from output: {missing}"

    def test_stats_preserved(self, runner, email_prompt, email_source):
        output = runner.run(email_prompt)
        missing = stats_preserved(email_source, output)
        assert missing == [], f"Stats missing from output: {missing}"
