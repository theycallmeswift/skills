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
        assert starts_with_h1(url_output.text), (
            f"URL output must start with '# '. First 80 chars: {url_output.text[:80]}"
        )

    def test_has_all_sections(self, url_output):
        missing = has_all_sections(url_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_markdown_link(self, url_output):
        title = h1_title(url_output.text)
        assert title is not None, "H1 title is missing"
        assert re.match(r"\[.+\]\(https?://.+\)", title), (
            f"URL input H1 should be a markdown link [Title](url). Got: {title}"
        )

    def test_share_contains_url(self, url_output, url_source):
        share = share_text(url_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert "http" in share, (
            f"URL input Share fence should contain the source URL. Share: {share}"
        )


class TestPastedInput:
    """Pasted text input: H1 is plain text (no link), Share has no URL."""

    def test_h1_is_plain_text(self, pasted_output):
        title = h1_title(pasted_output.text)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"Pasted input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, pasted_output):
        share = share_text(pasted_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"Pasted input Share fence should NOT contain a URL. Share: {share}"
        )


class TestFileInput:
    """File input: H1 is plain text (no link), Share has no URL."""

    def test_starts_with_h1(self, file_output):
        assert starts_with_h1(file_output.text), (
            f"File output must start with '# '. First 80 chars: {file_output.text[:80]}"
        )

    def test_has_all_sections(self, file_output):
        missing = has_all_sections(file_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_plain_text(self, file_output):
        title = h1_title(file_output.text)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"File input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, file_output):
        share = share_text(file_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"File input Share fence should NOT contain a URL. Share: {share}"
        )
