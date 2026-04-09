from tests.support.harness.matchers import EvalResult
from tests.support.harness.runner import RunResult


def _result(
    stdout="",
    final_message="",
    files_written=None,
    tool_trace=None,
    input_tokens=0,
    output_tokens=0,
    exit_code=0,
    turn_count=1,
    duration_s=0.0,
):
    run = RunResult(
        stdout=stdout,
        files_written=files_written or {},
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_s=duration_s,
        exit_code=exit_code,
        tool_trace=tool_trace or [],
        turn_count=turn_count,
        final_message=final_message,
    )
    return EvalResult(run)


# --- matches_regex / not_matches_regex ---


def test_matches_regex_on_final_message():
    r = _result(final_message="Hey, Sarah -- welcome")
    assert r.matches_regex(r"^Hey, Sarah --", on="final_message")


def test_matches_regex_fails_when_absent():
    r = _result(final_message="Hello world")
    assert not r.matches_regex(r"^Hey", on="stdout")


def test_matches_regex_min_count():
    r = _result(final_message="one? two?")
    assert r.matches_regex(r"\?", on="final_message", min=2)
    assert not r.matches_regex(r"\?", on="final_message", min=3)


def test_matches_regex_max_count():
    r = _result(final_message="one? two? three?")
    assert not r.matches_regex(r"\?", on="final_message", max=2)
    assert r.matches_regex(r"\?", on="final_message", max=3)


def test_not_matches_regex_passes_when_absent():
    r = _result(final_message="clean output")
    assert r.not_matches_regex(r"forbidden", on="final_message")


def test_not_matches_regex_fails_when_present():
    r = _result(final_message="forbidden word")
    assert not r.not_matches_regex(r"forbidden", on="final_message")


def test_matches_regex_on_stdout():
    r = _result(stdout="VISIBLE", final_message="HIDDEN")
    assert r.matches_regex("VISIBLE", on="stdout")
    assert not r.matches_regex("VISIBLE", on="final_message")


def test_matches_regex_on_files_glob():
    r = _result(files_written={"a.md": "alpha", "b.md": "beta", "c.txt": "gamma"})
    assert r.matches_regex("alpha", on="files.*.md")
    assert not r.matches_regex("gamma", on="files.*.md")


# --- contains / contains_all / not_contains ---


def test_contains_passes():
    r = _result(final_message="the answer is 42")
    assert r.contains("42", on="final_message")


def test_contains_fails():
    r = _result(final_message="hello")
    assert not r.contains("world", on="final_message")


def test_contains_all_passes():
    r = _result(final_message="450 fellows, 30% up, 92% rec rate")
    assert r.contains_all(["450", "30%", "92%"], on="final_message")


def test_contains_all_fails_on_missing():
    r = _result(final_message="450 fellows, 30% up")
    assert not r.contains_all(["450", "30%", "92%"], on="final_message")


def test_not_contains_passes():
    r = _result(final_message="clean")
    assert r.not_contains("dirty", on="final_message")


def test_not_contains_fails():
    r = _result(final_message="dirty string")
    assert not r.not_contains("dirty", on="final_message")


# --- output_len ---


def test_output_len_lte():
    r = _result(final_message="short")
    assert r.output_len_lte(100, on="final_message")
    assert not r.output_len_lte(3, on="final_message")


def test_output_len_gte():
    r = _result(final_message="hello world")
    assert r.output_len_gte(5, on="final_message")
    assert not r.output_len_gte(100, on="final_message")


# --- token_usage_lte ---


def test_token_usage_lte():
    r = _result(input_tokens=1000, output_tokens=500)
    assert r.token_usage_lte(2000)
    assert not r.token_usage_lte(1000)


# --- tool_called / not_tool_called ---


def test_tool_called():
    r = _result(tool_trace=[
        {"name": "mcp__brightdata__scrape_as_markdown", "input": {}, "turn": 1}
    ])
    assert r.tool_called("scrape_as_markdown")
    assert not r.tool_called("WebFetch")


def test_not_tool_called():
    r = _result(tool_trace=[{"name": "Read", "input": {}, "turn": 1}])
    assert r.not_tool_called("WebFetch")
    assert not r.not_tool_called("Read")


# --- skill_invoked / not_skill_invoked ---


def test_skill_invoked_bare():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}
    ])
    assert r.skill_invoked("ghostwrite")
    assert not r.skill_invoked("summarize")


def test_skill_invoked_prefixed():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 1}
    ])
    assert r.skill_invoked("ghostwrite")


def test_not_skill_invoked():
    r = _result(tool_trace=[{"name": "Read", "input": {}, "turn": 1}])
    assert r.not_skill_invoked("ghostwrite")


def test_not_skill_invoked_fails_when_fired():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}
    ])
    assert not r.not_skill_invoked("ghostwrite")


# --- trace_order ---


def test_trace_order_passes():
    r = _result(tool_trace=[
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
        {"name": "Bash", "input": {}, "turn": 1},
        {"name": "Write", "input": {}, "turn": 1},
    ])
    assert r.trace_order(["scrape_as_markdown", "Write"])


def test_trace_order_fails_wrong_order():
    r = _result(tool_trace=[
        {"name": "Write", "input": {}, "turn": 1},
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
    ])
    assert not r.trace_order(["scrape_as_markdown", "Write"])


# --- trace_count_lte ---


def test_trace_count_lte():
    r = _result(tool_trace=[{"name": "Bash", "input": {}, "turn": 1}] * 2)
    assert r.trace_count_lte("Bash", 3)
    assert not r.trace_count_lte("Bash", 1)


# --- turn_count_lte ---


def test_turn_count_lte():
    r = _result(turn_count=2)
    assert r.turn_count_lte(3)
    assert not r.turn_count_lte(1)


# --- file_contains / not_file_contains ---


def test_file_contains_text():
    r = _result(files_written={"references/specs/foo.md": "Out of scope: X"})
    assert r.file_contains("references/specs/*.md", text="Out of scope")
    assert not r.file_contains("references/specs/*.md", text="missing")


def test_file_contains_regex():
    r = _result(files_written={"a.md": "allowlist entry"})
    assert r.file_contains("*.md", regex=r"(?i)(allowlist|routing)")
    assert not r.file_contains("*.md", regex=r"(?i)missing")


def test_file_contains_no_matching_file():
    r = _result(files_written={"other.txt": "x"})
    assert not r.file_contains("*.md", text="x")


def test_not_file_contains():
    r = _result(files_written={"a.md": "clean content"})
    assert r.not_file_contains("*.md", text="forbidden")
    assert not r.not_file_contains("*.md", text="clean")
