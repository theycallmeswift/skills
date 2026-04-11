import dspy

from src.extractor import extract_demos, format_optimized_prompt


class _MockModule:
    def __init__(self, demos):
        self.demos = demos


def test_extract_demos_basic():
    module = _MockModule([dspy.Example(source="hello", rewritten="hi")])
    demos = extract_demos(module)
    assert demos == [{"source": "hello", "rewritten": "hi"}]


def test_extract_demos_empty():
    assert extract_demos(_MockModule([])) == []


def test_extract_demos_no_attr():
    assert extract_demos(object()) == []


def test_format_single_demo():
    demos = [{"source": "Hello world", "rewritten": "Hi"}]
    result = format_optimized_prompt(
        "Rewrite the input.",
        demos,
        input_fields=["source"],
        output_fields=["rewritten"],
    )
    assert result.startswith("## Examples")
    assert '**Input:**' in result
    assert 'source: "Hello world"' in result
    assert '**Output:**' in result
    assert 'rewritten: "Hi"' in result
    assert result.endswith("Rewrite the input.")


def test_format_no_demos():
    result = format_optimized_prompt("Original.", [], ["x"], ["y"])
    assert result == "Original."


def test_format_multiple_demos():
    demos = [
        {"source": "A", "rewritten": "a"},
        {"source": "B", "rewritten": "b"},
    ]
    result = format_optimized_prompt("Prompt.", demos, ["source"], ["rewritten"])
    assert result.count("**Input:**") == 2
    assert result.count("**Output:**") == 2
    assert result.endswith("Prompt.")


def test_format_multi_field():
    demos = [{"source": "hi", "medium": "email", "rewritten": "hey"}]
    result = format_optimized_prompt(
        "Prompt.", demos, ["source", "medium"], ["rewritten"]
    )
    assert 'source: "hi"' in result
    assert 'medium: "email"' in result
    assert 'rewritten: "hey"' in result
