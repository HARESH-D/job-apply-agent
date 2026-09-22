"""Build LinkedIn job search URLs from profile."""
from urllib.parse import quote_plus

from models import UserProfile

SENIORITY_MAP = {
    "entry": "2",
    "mid": "3",
    "senior": "4",
    "lead": "5",
}

WORK_MODE_MAP = {
    "remote": "2",
    "hybrid": "3",
    "onsite": "1",
}


def build_linkedin_search_urls(profile: UserProfile) -> list[str]:
    urls: list[str] = []
    roles = profile.target_roles or ["software engineer"]
    locations = profile.locations or [""]

    for role in roles[:3]:
        for location in locations[:2] or [""]:
            params = [
                f"keywords={quote_plus(role)}",
                f"location={quote_plus(location)}",
                "f_TPR=r86400",
                "sortBy=DD",
            ]
            levels = getattr(profile, "seniority_levels", None) or [
                getattr(profile, "seniority_level", "mid")
            ]
            exp_codes = list(
                dict.fromkeys(
                    SENIORITY_MAP[level]
                    for level in levels
                    if level in SENIORITY_MAP
                )
            )
            if exp_codes:
                params.append(f"f_E={quote_plus(','.join(exp_codes))}")

            modes = getattr(profile, "work_modes", None) or [
                getattr(profile, "work_mode", "any")
            ]
            work_codes = list(
                dict.fromkeys(
                    WORK_MODE_MAP[mode]
                    for mode in modes
                    if mode in WORK_MODE_MAP and mode != "any"
                )
            )
            if work_codes:
                params.append(f"f_WT={quote_plus(','.join(work_codes))}")
            urls.append("https://www.linkedin.com/jobs/search/?" + "&".join(params))
    return urls
