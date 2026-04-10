from tests.skills.ghostwrite.helpers import email_signoff, linkedin_hashtag_count


class TestEmailSignoff:
    def test_dash_swift(self):
        assert email_signoff("Some content.\n\n- Swift") is True

    def test_happy_hacking(self):
        assert email_signoff("Some content.\n\nHappy Hacking,\nSwift") is True

    def test_missing_signoff(self):
        assert email_signoff("Some content.\n\nBest,\nMike") is False

    def test_trailing_whitespace(self):
        assert email_signoff("Some content.\n\n- Swift  \n") is True


class TestLinkedinHashtagCount:
    def test_counts_hashtags(self):
        assert linkedin_hashtag_count("#MLH #AI #Hackathon #LearnByDoing") == 4

    def test_no_hashtags(self):
        assert linkedin_hashtag_count("No hashtags here.") == 0

    def test_inline_hashtags(self):
        assert linkedin_hashtag_count("Check out #MLH and #DEV today.") == 2
