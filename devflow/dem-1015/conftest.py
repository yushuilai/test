"""Pytest bootstrap for the dem-1015 acceptance suite.

Puts the project root (``devflow/dem-1015``) on ``sys.path`` so ``import src``
resolves whether pytest is invoked from the repository root or from the project
directory. Deliberately side-effect free: no fixtures, no mocks, no monkeypatching
of application code.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
