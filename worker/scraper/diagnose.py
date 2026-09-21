"""Diagnostic: prove where the scrape pipeline breaks. Read-only, writes debug artifacts."""
import asyncio
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
load_dotenv(ROOT / ".env")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "change-me-local-worker-key")
DEBUG_DIR = HERE / "debug"

CANDIDATE_CARD_SELECTORS = [
    "div.base-card",
    "div.job-card-container",
    "li.scaffold-layout__list-item",
    "ul.jobs-search__results-list > li",
    "div.jobs-search-results-list li",
    "[data-occludable-job-id]",
    "div[data-job-id]",
    "li[data-occludable-job-id]",
]

REAL_CAPTCHA_MARKERS = [
    "/checkpoint/challenge",
    "/authwall",
    "captcha-internal",
    "id=\"captcha\"",
]


def find_storage_state() -> Path | None:
    configured = os.getenv("LINKEDIN_STORAGE_STATE", "")
    candidates = []
    if configured:
        candidates.append(Path(configured))
        candidates.append((ROOT / configured).resolve())
        candidates.append((HERE / configured).resolve())
    candidates.append(HERE / "storage_state.json")
    candidates.extend(HERE.rglob("storage_state.json"))
    for c in candidates:
        try:
            if c.is_file():
                return c.resolve()
        except OSError:
            continue
    return None


async def get_search_urls() -> list[str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{API_BASE_URL}/profiles/active", headers={"X-API-Key": WORKER_API_KEY})
        r.raise_for_status()
        return r.json()["search_urls"]


async def main() -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("LAYER 1: session file")
    state = find_storage_state()
    print(f"  LINKEDIN_STORAGE_STATE env = {os.getenv('LINKEDIN_STORAGE_STATE')!r}")
    print(f"  resolved file              = {state}")
    if not state:
        print("  RESULT: FAIL — no session file found. Run login.py")
        return
    print(f"  size                       = {state.stat().st_size} bytes")

    print("=" * 70)
    print("LAYER 2: API search URLs")
    try:
        urls = await get_search_urls()
    except Exception as e:
        print(f"  RESULT: FAIL — {e}")
        return
    for u in urls:
        print(f"  {u}")
    if not urls:
        print("  RESULT: FAIL — no search URLs")
        return

    target = urls[0]
    headless = "--headful" not in sys.argv

    print("=" * 70)
    print(f"LAYER 3: page load (headless={headless})")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=str(state))
        page = await context.new_page()
        await page.goto(target, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        final_url = page.url
        title = await page.title()
        html = await page.content()
        print(f"  final URL = {final_url}")
        print(f"  title     = {title}")
        print(f"  html size = {len(html)} chars")

        (DEBUG_DIR / "page.html").write_text(html, encoding="utf-8")
        await page.screenshot(path=str(DEBUG_DIR / "page.png"), full_page=False)
        print(f"  saved     = {DEBUG_DIR / 'page.html'} , {DEBUG_DIR / 'page.png'}")

        print("=" * 70)
        print("LAYER 4: login state")
        logged_in = await page.query_selector("img.global-nav__me-photo, .global-nav__me, [data-control-name='nav.settings']")
        print(f"  authenticated nav present = {bool(logged_in)}")
        print(f"  redirected to login/authwall = {'login' in final_url or 'authwall' in final_url}")

        print("=" * 70)
        print("LAYER 5: CAPTCHA detection — current logic vs reality")
        low = html.lower()
        naive = ("captcha" in low) or ("challenge" in low)
        print(f"  CURRENT naive check says CAPTCHA = {naive}")
        for word in ("captcha", "challenge"):
            hits = [m.start() for m in re.finditer(word, low)]
            print(f"    '{word}' occurrences = {len(hits)}")
            for h in hits[:3]:
                snippet = html[max(0, h - 60):h + 60].replace("\n", " ")
                print(f"      ...{snippet}...")
        real = [m for m in REAL_CAPTCHA_MARKERS if m in low] or ("checkpoint/challenge" in final_url)
        print(f"  REAL captcha markers found = {real}")

        print("=" * 70)
        print("LAYER 6: selector counts")
        for sel in CANDIDATE_CARD_SELECTORS:
            try:
                n = len(await page.query_selector_all(sel))
            except Exception as e:
                n = f"error: {e}"
            print(f"  {n:>5}  {sel}")

        await browser.close()
    print("=" * 70)
    print("Done. Inspect debug/page.png to see what the browser actually rendered.")


if __name__ == "__main__":
    asyncio.run(main())
