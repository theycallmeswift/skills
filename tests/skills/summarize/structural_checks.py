def assert_structure(result):
    """Structural checks that apply to every summarize output (from lint.py)."""
    # Starts with H1 title
    assert result.matches_regex(r"(?m)^# \S", on="final_message")

    # Summary paragraph between title and first bullet list
    assert result.passes_rubric(
        "There is a non-list paragraph between the title and the first bullet list",
        on="final_message",
    )

    # Bullet count 1-8 (no padding)
    assert result.matches_regex(r"(?m)^- ", on="final_message", min=1, max=8)

    # Share block present
    assert result.matches_regex(
        r"(?im)^\s*(?:#+\s*share\b|\*\*share\*\*)", on="final_message"
    )

    # Comment block present
    assert result.matches_regex(
        r"(?im)^\s*(?:#+\s*comment\b|\*\*comment\*\*)", on="final_message"
    )

    # No em dashes
    assert result.not_contains("\u2014", on="final_message")

    # No narration prefix leaked into output
    assert result.not_matches_regex(
        r"^(Let me|Now I|I'll draft|I have the|Here's the summary)",
        on="final_message",
    )
