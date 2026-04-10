from textwrap import dedent

from tests.support.assertions.deterministic import (
    banned_words,
    email_signoff,
    linkedin_hashtag_count,
    long_sentences,
    no_em_dashes,
    slack_word_count,
    stats_preserved,
    urls_preserved,
)


class TestNoEmDashes:
    def test_clean_text(self):
        assert no_em_dashes("Hello, world.") == []

    def test_catches_em_dash(self):
        result = no_em_dashes("Hello — world.")
        assert len(result) == 1
        assert "—" in result[0]

    def test_multiple_lines(self):
        text = dedent("""\
            Line one is fine.
            Line two has — an em dash.
            Line three is fine.
            Line four — also bad.""")
        result = no_em_dashes(text)
        assert len(result) == 2


class TestLongSentences:
    def test_short_sentence(self):
        assert long_sentences("This is short.") == []

    def test_long_sentence(self):
        text = "This is a sentence that has way too many words in it and keeps going on and on and on and on and on and on."
        result = long_sentences(text, max_words=25)
        assert len(result) == 1

    def test_custom_max_words(self):
        text = "One two three four five six."
        assert long_sentences(text, max_words=5) == [text.strip()]
        assert long_sentences(text, max_words=10) == []


class TestBannedWords:
    def test_clean_text(self):
        assert banned_words("We built something cool.") == []

    def test_catches_synergy(self):
        result = banned_words("Great synergy between teams.")
        assert "synergy" in result

    def test_catches_delve(self):
        result = banned_words("Let's delve into this topic.")
        assert "delve" in result

    def test_catches_excited_to_share(self):
        result = banned_words("I'm excited to share this news.")
        assert "excited to share" in result

    def test_catches_game_changer(self):
        result = banned_words("This is a real game-changer for us.")
        assert "game-changer" in result

    def test_catches_paradigm_shift(self):
        result = banned_words("A paradigm shift in education.")
        assert "paradigm shift" in result

    def test_case_insensitive(self):
        result = banned_words("SYNERGY is key.")
        assert "synergy" in result


class TestUrlsPreserved:
    def test_all_present(self):
        source = "Check https://mlh.io and https://dev.to for details."
        output = "Visit https://mlh.io and https://dev.to."
        assert urls_preserved(source, output) == []

    def test_missing_url(self):
        source = "Check https://mlh.io and https://dev.to for details."
        output = "Visit https://mlh.io."
        result = urls_preserved(source, output)
        assert "https://dev.to" in result

    def test_no_urls_in_source(self):
        assert urls_preserved("No links here.", "No links here either.") == []


class TestStatsPreserved:
    def test_all_present(self):
        source = "We reached 500,000 developers and 1 in 3 CS students."
        output = "500,000 developers and 1 in 3 CS students joined."
        assert stats_preserved(source, output) == []

    def test_missing_stat(self):
        source = "We reached 500,000 developers and 1 in 3 CS students."
        output = "Many developers and 1 in 3 CS students joined."
        result = stats_preserved(source, output)
        assert "500,000" in result


class TestEmailSignoff:
    def test_dash_swift(self):
        assert email_signoff("Some content.\n\n- Swift") is True

    def test_happy_hacking(self):
        assert email_signoff("Some content.\n\nHappy Hacking,\nSwift") is True

    def test_missing_signoff(self):
        assert email_signoff("Some content.\n\nBest,\nMike") is False

    def test_trailing_whitespace(self):
        assert email_signoff("Some content.\n\n- Swift  \n") is True


class TestSlackWordCount:
    def test_counts_words(self):
        assert slack_word_count("Hello world, this is a test.") == 6

    def test_empty_string(self):
        assert slack_word_count("") == 0


class TestLinkedinHashtagCount:
    def test_counts_hashtags(self):
        assert linkedin_hashtag_count("#MLH #AI #Hackathon #LearnByDoing") == 4

    def test_no_hashtags(self):
        assert linkedin_hashtag_count("No hashtags here.") == 0

    def test_inline_hashtags(self):
        assert linkedin_hashtag_count("Check out #MLH and #DEV today.") == 2
