import dspy

from src.bridge import build_signature, rows_to_examples


def test_build_signature_single_input_output():
    sig = build_signature("Rewrite the input.", ["source"], ["rewritten"])
    assert "source" in sig.input_fields
    assert "rewritten" in sig.output_fields
    assert len(sig.input_fields) == 1
    assert len(sig.output_fields) == 1


def test_build_signature_doc():
    sig = build_signature("Rewrite the input.", ["source"], ["rewritten"])
    assert sig.__doc__ == "Rewrite the input."


def test_build_signature_multi_input():
    sig = build_signature("Do the thing.", ["source", "medium"], ["rewritten"])
    assert "source" in sig.input_fields
    assert "medium" in sig.input_fields
    assert "rewritten" in sig.output_fields
    assert len(sig.input_fields) == 2


def test_rows_to_examples_basic():
    rows = [{"source": "hello", "rewritten": "hi"}]
    examples = rows_to_examples(rows, ["source"])
    assert len(examples) == 1
    assert examples[0].source == "hello"
    assert examples[0].rewritten == "hi"
    assert list(examples[0].inputs().keys()) == ["source"]


def test_rows_to_examples_multi_input():
    rows = [{"source": "hi", "medium": "email", "rewritten": "hey"}]
    examples = rows_to_examples(rows, ["source", "medium"])
    assert set(examples[0].inputs().keys()) == {"source", "medium"}


def test_rows_to_examples_multiple_rows():
    rows = [
        {"source": "a", "rewritten": "A"},
        {"source": "b", "rewritten": "B"},
    ]
    examples = rows_to_examples(rows, ["source"])
    assert len(examples) == 2
    assert examples[1].source == "b"
