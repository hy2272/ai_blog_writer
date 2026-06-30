#!/usr/bin/env python3
"""CLI wrapper for the default Xiaohongshu long-image post adapter."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.xiaohongshu.adapter import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
