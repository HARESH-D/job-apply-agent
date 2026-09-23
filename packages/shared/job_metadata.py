"""Pure normalization helpers shared by scraper and API tests."""
import re
from datetime import datetime, timedelta, timezone


def detect_workplace_type(text: str) -> str:
    normalized = text.lower().replace("-", "").replace(" ", "")
    if "onsite" in normalized:
        return "onsite"
    if "hybrid" in normalized:
        return "hybrid"
    if "remote" in normalized or "virtual" in normalized:
        return "remote"
    return "unknown"


def is_closed_application_text(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "no longer accepting applications",
            "applications are closed",
            "job is no longer available",
            "position has been filled",
        )
    )


def parse_linkedin_posted_at(
    text: str, now: datetime | None = None
) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    match = re.search(
        r"(\d+)\s*(minute|hour|day|week)s?\s+ago",
        text.lower(),
    )
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    delta = {
        "minute": timedelta(minutes=value),
        "hour": timedelta(hours=value),
        "day": timedelta(days=value),
        "week": timedelta(weeks=value),
    }[unit]
    return now - delta
