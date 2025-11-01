import sys
from pathlib import Path

# Ensure the project root (backend/) is on sys.path so tests can import the `app` package.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
