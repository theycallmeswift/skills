"""Shared test configuration."""

from __future__ import annotations

import sys
from pathlib import Path

TESTS = Path(__file__).parent
sys.path.insert(0, str(TESTS))
