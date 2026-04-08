import argparse
import asyncio
import sys
from pathlib import Path

from .orchestrator import run_evals
from .reporter import make_reporter


def main() -> int:
    parser = argparse.ArgumentParser(prog="tests.support.harness")
    parser.add_argument("names", nargs="*", help="filter by suite name")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-baseline", action="store_true")
    parser.add_argument(
        "--model",
        default=None,
        help="Override the model used by the agent SDK (e.g. claude-haiku-4-5-20251001). "
             "Defaults to the SDK session model.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    reporter = make_reporter()

    return asyncio.run(run_evals(
        project_root=project_root,
        names=args.names or None,
        baseline=not args.no_baseline,
        verbose=args.verbose,
        reporter=reporter,
        model=args.model,
    ))

if __name__ == "__main__":
    sys.exit(main())
