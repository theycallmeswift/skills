def assert_core_rules(result):
    """Core voice rules that apply to every ghostwrite output (from lint.py)."""
    # No em dashes — ever
    assert result.not_contains("\u2014", on="final_message")

    # No banned phrases
    assert result.not_matches_regex(r"\bexcited to share\b", on="final_message")
    assert result.not_matches_regex(r"\bleverage[ds]?\b", on="final_message")
    assert result.not_matches_regex(r"\becosystem\b", on="final_message")
    assert result.not_matches_regex(r"\bdelve[ds]?\b", on="final_message")
    assert result.not_matches_regex(r"\bsynergy\b", on="final_message")
    assert result.not_matches_regex(r"\bgame[- ]changer\b", on="final_message")
    assert result.not_matches_regex(r"\bparadigm shift\b", on="final_message")
    assert result.not_matches_regex(r"\babsolutely incredible\b", on="final_message")
    assert result.not_matches_regex(r"Let me know in the comments", on="final_message")
