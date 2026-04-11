#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dspy

import src.optimizers  # noqa: F401 — triggers strategy registration
from src.bridge import build_signature, rows_to_examples
from src.parser import load_csv, parse_prompt, read_prompt
from src.strategy import get_strategy


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Optimize a prompt using DSPy strategies")
    parser.add_argument("--prompt", required=True, help="Path to prompt file, or - for stdin")
    parser.add_argument("--training-data", required=True, help="Path to CSV file")
    parser.add_argument(
        "--output-fields", required=True, help="Comma-separated output column names"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5-20251001",
        help="Model identifier for DSPy (default: anthropic/claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--strategy",
        default="bootstrap_fewshot",
        help="Optimization strategy (default: bootstrap_fewshot)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to JSON file with strategy-specific configuration",
    )

    args = parser.parse_args(argv)
    args.output_fields = [f.strip() for f in args.output_fields.split(",")]
    return args


def load_config(config_path):
    """Load strategy config from JSON file. Returns empty dict if path is None."""
    if config_path is None:
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)


def format_metadata(metadata):
    """Format metadata dict as YAML-style key: value lines with separator."""
    lines = [f"{k}: {v}" for k, v in metadata.items()]
    return "\n---\n" + "\n".join(lines)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set. Export it before running.", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    config = load_config(args.config)

    lm = dspy.LM(args.model)
    dspy.configure(lm=lm)

    content = read_prompt(args.prompt)
    _, prompt = parse_prompt(content)
    headers, rows = load_csv(args.training_data)
    input_fields = [h for h in headers if h not in args.output_fields]

    signature = build_signature(prompt, input_fields, args.output_fields)
    examples = rows_to_examples(rows, input_fields)

    strategy_cls = get_strategy(args.strategy)
    strategy = strategy_cls()
    result = strategy.optimize(signature_cls=signature, examples=examples, config=config)

    print(result.prompt)
    print(format_metadata(result.metadata))


if __name__ == "__main__":
    main()
