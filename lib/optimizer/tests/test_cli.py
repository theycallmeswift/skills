from optimize_prompt import parse_args


def test_parse_args_required():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"])
    assert args.prompt == "p.md"
    assert args.training_data == "t.csv"
    assert args.output_fields == ["out"]


def test_parse_args_defaults():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"])
    assert args.model == "haiku"
    assert args.strategy == "bootstrap_fewshot"
    assert args.max_demos == 4


def test_parse_args_custom_values():
    args = parse_args([
        "--prompt", "p.md",
        "--training-data", "t.csv",
        "--output-fields", "out",
        "--model", "sonnet",
        "--max-demos", "8",
    ])
    assert args.model == "sonnet"
    assert args.max_demos == 8


def test_parse_args_multi_output_fields():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "a,b"])
    assert args.output_fields == ["a", "b"]
