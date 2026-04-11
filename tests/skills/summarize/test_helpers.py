from textwrap import dedent

from tests.skills.summarize.helpers import (
    cliff_notes_bullets,
    comment_text,
    h1_title,
    has_all_sections,
    share_text,
    starts_with_h1,
    tldr_text,
    word_count,
)


class TestStartsWithH1:
    def test_starts_with_hash(self):
        assert starts_with_h1("# My Title\n\n## TL;DR\n...") is True

    def test_starts_with_preamble(self):
        assert starts_with_h1("Here's the summary:\n\n# My Title\n...") is False

    def test_empty_string(self):
        assert starts_with_h1("") is False


class TestH1Title:
    def test_extracts_plain_title(self):
        text = "# My Document Title\n\n## TL;DR\nSome text."
        assert h1_title(text) == "My Document Title"

    def test_extracts_link_title(self):
        text = "# [Article Title](https://example.com)\n\n## TL;DR\nSome text."
        assert h1_title(text) == "[Article Title](https://example.com)"

    def test_returns_none_when_missing(self):
        assert h1_title("No heading here.") is None


class TestHasAllSections:
    def test_all_present(self):
        text = dedent("""\
            # Title

            ## TL;DR

            Summary here.

            ## Cliff Notes

            - Point one

            ## Share

            ```
            Hot take here
            ```

            ## Comment

            ```
            My comment
            ```""")
        assert has_all_sections(text) == []

    def test_missing_sections(self):
        text = "# Title\n\n## TL;DR\n\nSummary."
        missing = has_all_sections(text)
        assert "## Cliff Notes" in missing
        assert "## Share" in missing
        assert "## Comment" in missing


class TestTldrText:
    def test_extracts_tldr(self):
        text = dedent("""\
            # Title

            ## TL;DR

            This is the summary.

            ## Cliff Notes

            - Point one""")
        assert tldr_text(text) == "This is the summary."

    def test_returns_none_when_missing(self):
        assert tldr_text("# Title\n\n## Cliff Notes\n\n- One") is None


class TestCliffNotesBullets:
    def test_counts_bullets(self):
        text = dedent("""\
            # Title

            ## TL;DR

            Summary.

            ## Cliff Notes

            - First point
            - Second point
            - Third point

            ## Share

            ```
            Hot take
            ```""")
        bullets = cliff_notes_bullets(text)
        assert len(bullets) == 3

    def test_returns_empty_when_missing(self):
        assert cliff_notes_bullets("# Title\n\n## TL;DR\nText.") == []


class TestShareText:
    def test_extracts_share_content(self):
        text = dedent("""\
            ## Share

            ```
            This is the hot take
            https://example.com
            ```

            ## Comment""")
        assert "This is the hot take" in share_text(text)

    def test_returns_none_when_missing(self):
        assert share_text("# Title\n\n## TL;DR\nText.") is None


class TestCommentText:
    def test_extracts_comment_content(self):
        text = dedent("""\
            ## Comment

            ```
            Great take, but shipping matters more than architecture.
            ```""")
        assert "shipping matters more" in comment_text(text)

    def test_returns_none_when_missing(self):
        assert comment_text("# Title\n\n## TL;DR\nText.") is None


class TestWordCount:
    def test_counts_words(self):
        assert word_count("Hello world, this is a test.") == 6

    def test_empty_string(self):
        assert word_count("") == 0
