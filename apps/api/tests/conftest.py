import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "apps" / "api"

for path in (ROOT, API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
