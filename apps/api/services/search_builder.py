"""Build LinkedIn job search URLs from profile."""
from urllib.parse import quote_plus

from models import UserProfile

SENIORITY_MAP = {
    "entry": "1",
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
            exp = SENIORITY_MAP.get(profile.seniority_level)
            if exp:
                params.append(f"f_E={exp}")
            wt = WORK_MODE_MAP.get(profile.work_mode)
            if wt and profile.work_mode != "any":
                params.append(f"f_WT={wt}")
            urls.append("https://www.linkedin.com/jobs/search/?" + "&".join(params))
    return urls
