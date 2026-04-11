import os
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "bin"))


def pytest_collection_modifyitems(config, items):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        skip = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
