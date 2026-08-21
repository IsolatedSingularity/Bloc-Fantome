"""Shared test path setup; individual test order must not affect imports."""

from pathlib import Path
import sys


CODE_DIR = Path(__file__).resolve().parents[1] / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
