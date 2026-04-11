import dspy


def build_signature(prompt, input_fields, output_fields):
    """Create a DSPy Signature class from a prompt and field definitions.

    The prompt becomes the Signature's __doc__ (instruction).
    Column names become InputField/OutputField definitions.
    """
    fields = {}
    for name in input_fields:
        fields[name] = dspy.InputField()
    for name in output_fields:
        fields[name] = dspy.OutputField()

    return type("DynamicSignature", (dspy.Signature,), {"__doc__": prompt, **fields})


def rows_to_examples(rows, input_fields):
    """Convert CSV row dicts to DSPy Example objects with input marking."""
    examples = []
    for row in rows:
        ex = dspy.Example(**row).with_inputs(*input_fields)
        examples.append(ex)
    return examples
