"""LinkedIn job scraper via Playwright (authenticated jobs UI)."""
import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import ElementHandle, Page, async_playwright

BASE_URL = "https://www.linkedin.com"

SELECTORS = {
    "job_list_item": "li[data-occludable-job-id]",
    "job_id_attr": "data-occludable-job-id",
    "job_title": "a.job-card-container__link, .job-card-list__title--link",
    "job_company": ".artdeco-entity-lockup__subtitle",
    "job_location": ".artdeco-entity-lockup__caption, .job-card-container__metadata-wrapper",
    "job_link": "a[href*='/jobs/view/']",
    "jd_pane": "#job-details, .jobs-description__content, .jobs-box__html-content",
    "results_container": ".scaffold-layout__list > div, .jobs-search-results-list",
    "authenticated_nav": "img.global-nav__me-photo, .global-nav__me",
}

# LinkedIn loads Google reCAPTCHA on normal pages, so the word "captcha" in the
# HTML proves nothing. Only these signals mean the session is actually blocked.
BLOCK_URL_MARKERS = ("/checkpoint/challenge", "/authwall", "/uas/login", "/login")
BLOCK_DOM_SELECTORS = (
    "form.challenge-form",
    "#captcha-internal",
    "div.authwall",
    "input[name='security-challenge-id']",
)


async def _random_delay(min_s: float = 2.0, max_s: float = 5.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def detect_block(page: Page) -> str | None:
    """Return a reason string if LinkedIn blocked us, else None."""
    url = page.url.lower()
    for marker in BLOCK_URL_MARKERS:
        if marker in url:
            return f"Session invalid or challenged (redirected to {marker}). Run: python login.py"
    for selector in BLOCK_DOM_SELECTORS:
        if await page.query_selector(selector):
            return f"Security challenge element found ({selector}). Log in manually, then rerun login.py"
    return None


async def _text_of(scope: ElementHandle, selector: str) -> str:
    el = await scope.query_selector(selector)
    if not el:
        return ""
    return (await el.inner_text()).strip().split("\n")[0].strip()


async def _read_jd_pane(page: Page) -> str:
    el = await page.query_selector(SELECTORS["jd_pane"])
    if not el:
        return ""
    return (await el.inner_text()).strip()


async def _collect_cards(page: Page, max_jobs: int) -> list[dict[str, Any]]:
    """The results list is virtualized: occluded items render no text, so scroll
    incrementally and harvest each item as it hydrates."""
    collected: dict[str, dict[str, Any]] = {}

    for _ in range(15):
        items = await page.query_selector_all(SELECTORS["job_list_item"])
        if not items:
            break

        for item in items:
            job_id = await item.get_attribute(SELECTORS["job_id_attr"]) or ""
            if not job_id or job_id in collected:
                continue
            title = await _text_of(item, SELECTORS["job_title"])
            if not title:
                continue
            collected[job_id] = {
                "external_id": job_id,
                "title": title,
                "company": await _text_of(item, SELECTORS["job_company"]),
                "location": await _text_of(item, SELECTORS["job_location"]),
                "url": f"{BASE_URL}/jobs/view/{job_id}/",
            }

        if len(collected) >= max_jobs:
            break

        await items[-1].scroll_into_view_if_needed()
        await page.wait_for_timeout(random.randint(700, 1300))

    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(400)
    return list(collected.values())


async def _extract_jd_from_pane(page: Page, job_id: str) -> str:
    """Click the card in the results list and read the right-hand detail pane.
    The standalone /jobs/view/ page uses a different layout that has no stable
    description container, so the pane is the reliable source."""
    link = await page.query_selector(
        f"{SELECTORS['job_list_item']}[{SELECTORS['job_id_attr']}='{job_id}'] {SELECTORS['job_link']}"
    )
    if not link:
        return ""
    try:
        await link.scroll_into_view_if_needed()
        await link.click()
    except Exception:
        return ""

    for _ in range(12):
        await page.wait_for_timeout(500)
        text = await _read_jd_pane(page)
        if len(text) > 200:
            return text
    return await _read_jd_pane(page)


async def scrape_linkedin_jobs(
    search_urls: list[str],
    storage_state_path: str,
    max_jobs: int = 50,
    headless: bool = True,
    verbose: bool = True,
) -> tuple[list[dict[str, Any]], str | None]:
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    block_error: str | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=storage_state_path)
        page = await context.new_page()

        try:
            for search_url in search_urls:
                if len(jobs) >= max_jobs:
                    break

                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)

                block_error = await detect_block(page)
                if block_error:
                    break

                try:
                    await page.wait_for_selector(SELECTORS["job_list_item"], timeout=20000)
                except Exception:
                    if verbose:
                        print(f"  no job cards rendered for: {search_url}")
                    continue

                cards = await _collect_cards(page, max_jobs=max_jobs - len(jobs))
                if verbose:
                    query = search_url.split("keywords=")[-1].split("&")[0].replace("+", " ")
                    print(f"  {len(cards)} cards for '{query}'")

                for card in cards:
                    if len(jobs) >= max_jobs:
                        break
                    if card["external_id"] in seen_ids:
                        continue
                    seen_ids.add(card["external_id"])

                    jd_text = await _extract_jd_from_pane(page, card["external_id"])
                    jobs.append({
                        "source": "linkedin",
                        "external_id": card["external_id"],
                        "title": card["title"],
                        "company": card["company"],
                        "location": card["location"],
                        "url": card["url"],
                        "jd_text": jd_text,
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                        "raw_json": card,
                    })
                    if verbose:
                        print(f"    + {card['title'][:45]:45} | {card['company'][:22]:22} | jd={len(jd_text)} chars")
                    await _random_delay(1.5, 3.0)
        finally:
            await browser.close()

    return jobs, block_error


async def login_and_save_session(storage_state_path: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("Log into LinkedIn in the browser window. Press Enter here when done.")
        input()
        await context.storage_state(path=storage_state_path)
        await browser.close()
