"""Make every skill's scripts/ importable as bare modules in tests.

tests/skills/<name>/scripts/ mirrors skills/<name>/scripts/; this one conftest serves them all.
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"
for scripts in sorted(SKILLS.glob("*/scripts")):
    sys.path.insert(0, str(scripts))
