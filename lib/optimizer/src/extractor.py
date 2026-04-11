def extract_demos(compiled_module):
    """Pull few-shot demos from a compiled DSPy module.

    Returns a list of plain dicts, one per demo.
    """
    demos = getattr(compiled_module, "demos", None) or []
    return [{k: demo[k] for k in demo.keys()} for demo in demos]


def format_optimized_prompt(original_prompt, demos, input_fields, output_fields):
    """Format demos as natural language examples, append after original prompt.

    Returns the original prompt unchanged if demos is empty.
    """
    if not demos:
        return original_prompt

    sections = []
    for demo in demos:
        input_lines = "\n".join(f'{f}: "{demo[f]}"' for f in input_fields if f in demo)
        output_lines = "\n".join(f'{f}: "{demo[f]}"' for f in output_fields if f in demo)
        sections.append(f"**Input:**\n{input_lines}\n\n**Output:**\n{output_lines}")

    examples_block = "## Examples\n\n" + "\n\n---\n\n".join(sections)
    return f"{original_prompt}\n\n---\n\n{examples_block}"
