from fnmatch import fnmatch


def test_asks_clarifying_questions(result):
    assert result.passes_rubric(
        "Early in the conversation, the agent asks clarifying questions "
        "before proposing a design.",
        on="stdout",
    )


def test_proposes_approaches(result):
    assert result.passes_rubric(
        "The agent proposes 2-3 distinct approaches with trade-offs.",
        on="stdout",
    )


def test_gives_recommendation(result):
    assert result.passes_rubric(
        "The agent includes a clear recommendation with reasoning "
        "for which approach to use.",
        on="stdout",
    )


def test_no_implementation_code(result):
    assert not any(fnmatch(f, "*.py") for f in result.files_written)
    assert not any(fnmatch(f, "*.js") for f in result.files_written)
    assert not any(fnmatch(f, "*.ts") for f in result.files_written)
    assert "package.json" not in result.files_written


def test_writes_exactly_one_spec(result):
    specs = [f for f in result.files_written if fnmatch(f, "references/specs/*.md")]
    assert len(specs) == 1
