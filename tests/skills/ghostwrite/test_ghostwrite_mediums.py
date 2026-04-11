import re

from tests.skills.ghostwrite.helpers import email_signoff, linkedin_hashtag_count
from tests.support.assertions import judge


class TestEmailMedium:
    def test_email_has_valid_signoff(self, email_output):
        assert email_signoff(email_output.text), (
            f"Email missing valid sign-off ('- Swift' or 'Happy Hacking,\\nSwift'). "
            f"Ending: ...{email_output.text[-100:]}"
        )

    def test_email_greeting_format(self, email_output):
        assert re.search(r"Hey,\s+\w+\s+--", email_output.text), (
            f"Email missing 'Hey, [Name] --' greeting. First line: {email_output.text.splitlines()[0]}"
        )

    def test_email_opens_with_point(self, runner, email_output, email_source):
        result = judge(
            source=email_source,
            output=email_output.text,
            rubric="The first sentence after the greeting contains the main point, update, or ask. Not a pleasantry or context-setting preamble.",
            runner=runner,
        )
        assert result.passed, f"Email doesn't open with the point: {result.reasoning}"


class TestLinkedinMedium:
    def test_linkedin_word_count(self, linkedin_output):
        words = len(linkedin_output.text.split())
        assert words <= 200, f"LinkedIn post is {words} words (expected under 200)"

    def test_linkedin_hashtag_count(self, linkedin_output):
        count = linkedin_hashtag_count(linkedin_output.text)
        assert 4 <= count <= 7, f"LinkedIn post has {count} hashtags (expected 4-7)"

    def test_linkedin_hooks_first(self, runner, linkedin_output, linkedin_source):
        result = judge(
            source=linkedin_source,
            output=linkedin_output.text,
            rubric="The opening line is a hook that challenges, quotes, or directly addresses the reader. It does NOT start with 'I'm excited to share' or 'I recently' or similar preamble.",
            runner=runner,
        )
        assert result.passed, f"LinkedIn doesn't hook first: {result.reasoning}"


class TestSlackMedium:
    def test_slack_under_60_words(self, slack_output):
        count = len(slack_output.text.split())
        assert count <= 60, f"Slack message is {count} words (max 60)"

    def test_slack_no_markdown_headers(self, slack_output):
        header_lines = [line for line in slack_output.text.splitlines() if re.match(r"^#+\s", line)]
        assert header_lines == [], (
            f"Slack doesn't support markdown headers: {header_lines}"
        )

    def test_slack_ask_first(self, runner, slack_output, slack_source):
        result = judge(
            source=slack_source,
            output=slack_output.text,
            rubric="The main point or ask appears in the first 1-2 sentences, not buried after context or preamble.",
            runner=runner,
        )
        assert result.passed, f"Slack doesn't put ask first: {result.reasoning}"


class TestBlogMedium:
    def test_blog_has_section_headers(self, blog_output):
        headers = [line for line in blog_output.text.splitlines() if re.match(r"^#{1,3}\s", line)]
        assert len(headers) >= 2, (
            f"Blog post should have section headers (## or ###). Found {len(headers)}"
        )
