"""Resolve worker paths consistently regardless of the shell's working directory."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def resolve_storage_state() -> Path:
    configured = os.getenv("LINKEDIN_STORAGE_STATE", "").strip()
    if not configured:
        return HERE / "storage_state.json"
    path = Path(configured)
    if path.is_absolute():
        return path
    return (ROOT / configured).resolve()
