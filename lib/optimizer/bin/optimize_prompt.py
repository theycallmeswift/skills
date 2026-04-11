#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4-5-20251001",
    "sonnet": "anthropic/claude-sonnet-4-6-20250514",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Optimize a prompt with few-shot examples")
    parser.add_argument("--prompt", required=True, help="Path to prompt file, or - for stdin")
    parser.add_argument("--training-data", required=True, help="Path to CSV file")
    parser.add_argument(
        "--output-fields", required=True, help="Comma-separated output column names"
    )
    parser.add_argument(
        "--model",
        default="haiku",
        choices=list(MODEL_MAP.keys()),
        help="Target model (default: haiku)",
    )
    parser.add_argument(
        "--strategy",
        default="bootstrap_fewshot",
        help="Optimization strategy (default: bootstrap_fewshot)",
    )
    parser.add_argument(
        "--max-demos", type=int, default=4, help="Max few-shot examples to include (default: 4)"
    )
    args = parser.parse_args(argv)
    args.output_fields = [f.strip() for f in args.output_fields.split(",")]
    return args


def main():
    import dspy

    from src.bridge import build_signature, rows_to_examples
    from src.extractor import extract_demos, format_optimized_prompt
    from src.optimizer import optimize
    from src.parser import load_csv, parse_prompt

    args = parse_args()

    lm = dspy.LM(MODEL_MAP[args.model])
    dspy.configure(lm=lm)

    _, prompt = parse_prompt(args.prompt)
    headers, rows = load_csv(args.training_data)
    input_fields = [h for h in headers if h not in args.output_fields]

    signature = build_signature(prompt, input_fields, args.output_fields)
    examples = rows_to_examples(rows, input_fields)
    compiled = optimize(signature, examples, max_demos=args.max_demos)

    demos = extract_demos(compiled)
    optimized = format_optimized_prompt(prompt, demos, input_fields, args.output_fields)
    print(optimized)


if __name__ == "__main__":
    main()
