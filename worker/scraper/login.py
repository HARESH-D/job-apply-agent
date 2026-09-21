"""One-time LinkedIn login — saves storage_state.json locally."""
import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from linkedin_scraper import login_and_save_session
from paths import resolve_storage_state

if __name__ == "__main__":
    storage_state = resolve_storage_state()
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(login_and_save_session(str(storage_state)))
    print(f"Session saved to {storage_state}")
