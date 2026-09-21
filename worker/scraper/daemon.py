"""Local scraper daemon — runs every 6 hours."""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from linkedin_scraper import scrape_linkedin_jobs
from paths import resolve_storage_state

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "change-me-local-worker-key")
STORAGE_STATE = resolve_storage_state()
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))


def _headers() -> dict[str, str]:
    return {"X-API-Key": WORKER_API_KEY}


async def run_scrape_once() -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(f"{API_BASE_URL}/profiles/active", headers=_headers())
        if resp.status_code == 404:
            print("No active profile — create one in the UI first.")
            return
        resp.raise_for_status()
        config = resp.json()
        profile = config["profile"]
        search_urls = config["search_urls"]
        profile_id = profile["id"]
        max_jobs = profile.get("max_jobs_per_run", 50)

        started_at = datetime.now(timezone.utc)
        errors = ""
        status = "completed"
        jobs_found = 0

        if not STORAGE_STATE.exists():
            errors = f"Missing session file: {STORAGE_STATE}. Run: python login.py"
            status = "failed"
        else:
            print(f"Session: {STORAGE_STATE}")
            print(f"Searching {len(search_urls)} queries, max {max_jobs} jobs...")
            jobs, blocked = await scrape_linkedin_jobs(
                search_urls=search_urls,
                storage_state_path=str(STORAGE_STATE),
                max_jobs=max_jobs,
            )
            jobs_found = len(jobs)
            if blocked:
                errors = blocked
                status = "captcha"
                print(f"BLOCKED: {blocked}")
            elif not jobs:
                errors = "No job cards found — LinkedIn markup may have changed. Run: python diagnose.py"
                status = "failed"
            else:
                bulk = await client.post(
                    f"{API_BASE_URL}/jobs/bulk",
                    headers=_headers(),
                    json={"profile_id": profile_id, "jobs": jobs},
                )
                bulk.raise_for_status()
                print(f"Ingested: {bulk.json()}")

        completed_at = datetime.now(timezone.utc)
        run_resp = await client.post(
            f"{API_BASE_URL}/scrape-runs",
            headers=_headers(),
            json={
                "profile_id": profile_id,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "jobs_found": jobs_found,
                "errors": errors,
                "status": status,
            },
        )
        run_resp.raise_for_status()
        print(f"Scrape run: {status}, jobs={jobs_found}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_scrape_once())
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: asyncio.run(run_scrape_once()), "interval", hours=SCRAPE_INTERVAL_HOURS)
    print(f"Scraper daemon started — every {SCRAPE_INTERVAL_HOURS}h. Use --once for immediate run.")
    scheduler.start()


if __name__ == "__main__":
    main()
