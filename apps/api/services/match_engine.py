"""Hybrid job-profile matching engine."""
import re
from datetime import datetime, timezone

from models import JobPosting, UserProfile
from packages.shared.schemas import ParsedResume


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "its", "of", "on", "or", "our", "that", "the", "to", "we",
    "will", "with", "you", "your", "work", "team", "role", "job", "years", "year",
    "experience", "strong", "good", "new", "other", "who", "this", "they", "their",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", text.lower())


def _meaningful_terms(text: str) -> set[str]:
    """Terms worth scoring on. Digits are dropped: phone numbers and postcodes
    leak in from resume parsing and can never legitimately match a job."""
    return {
        t for t in _tokenize(text)
        if len(t) > 2 and t not in STOPWORDS and not any(ch.isdigit() for ch in t)
    }


def _semantic_coverage(profile_text: str, job_text: str) -> float:
    """Fraction of the profile's distinctive terms that appear in the job text.

    Raw-count cosine is unusable here: a ~30-token profile against a 2000-word JD
    is length-penalized toward zero no matter how well they match. Coverage is
    length-robust and keeps the 0-1 range meaningful.
    """
    profile_terms = _meaningful_terms(profile_text)
    if not profile_terms:
        return 0.0
    job_terms = _meaningful_terms(job_text)
    if not job_terms:
        return 0.0
    return len(profile_terms & job_terms) / len(profile_terms)


def _skill_overlap(profile_skills: list[str], jd_text: str) -> tuple[float, list[str]]:
    """Whole-word / token skill hit — avoids 'go' matching inside 'golang' etc."""
    matched: list[str] = []
    for skill in profile_skills:
        token = skill.strip()
        if not token:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.IGNORECASE)
        if pattern.search(jd_text):
            matched.append(skill)
    if not profile_skills:
        return 0.0, []
    return len(matched) / len(profile_skills), matched


def _role_match(target_roles: list[str], title: str, jd_text: str) -> tuple[float, list[str]]:
    """Best single-role fit, scored on the title first.

    Averaging across all target roles punished a perfect match on one role just
    because the other target role was absent, so take the best role instead.
    """
    if not target_roles:
        return 0.5, []

    title_terms = _meaningful_terms(title)
    jd_terms = _meaningful_terms(jd_text)
    best = 0.0
    hits: list[str] = []

    for role in target_roles:
        role_terms = _meaningful_terms(role)
        if not role_terms:
            continue
        title_fit = len(role_terms & title_terms) / len(role_terms)
        jd_fit = len(role_terms & jd_terms) / len(role_terms)
        score = max(title_fit, 0.6 * jd_fit)
        if score > best:
            best = score
        if title_fit >= 0.5 or role.lower() in jd_text.lower():
            hits.append(role)

    return min(best, 1.0), hits


def _exp_fit(profile: UserProfile, jd_text: str) -> float:
    years = profile.experience_years
    jd_lower = jd_text.lower()
    required = _extract_required_years(jd_text)
    if required is not None:
        if required > years:
            return 0.0
        return 1.0 if years - required <= 3 else 0.8
    if years <= 2 and any(k in jd_lower for k in ("junior", "entry", "0-2", "1-2")):
        return 1.0
    if 2 < years <= 5 and any(k in jd_lower for k in ("mid", "2-5", "3-5", "associate")):
        return 1.0
    if years > 5 and any(k in jd_lower for k in ("senior", "lead", "5+", "staff")):
        return 1.0
    return 0.5


def _extract_required_years(text: str) -> int | None:
    """Extract the strongest explicit minimum-experience requirement."""
    lowered = text.lower()
    patterns = (
        r"(?:minimum|min\.?|at\s+least)\s+(?:of\s+)?(\d{1,2})\s*\+?\s*years?",
        r"(\d{1,2})\s*(?:-|–|—|to)\s*\d{1,2}\s*years?",
        r"(\d{1,2})\s*\+\s*years?",
        r"(?:requires?|required|need(?:ed)?|have)\D{0,24}(\d{1,2})\s+years?",
    )
    values = [
        int(match.group(1))
        for pattern in patterns
        for match in re.finditer(pattern, lowered)
    ]
    return max(values) if values else None


def _selected_levels(profile: UserProfile) -> set[str]:
    values = getattr(profile, "seniority_levels", None) or [
        getattr(profile, "seniority_level", "mid")
    ]
    return {getattr(value, "value", value) for value in values}


def _title_level_allowed(profile: UserProfile, title: str) -> bool:
    levels = _selected_levels(profile)
    title_lower = title.lower()
    if re.search(r"\b(director|executive|principal|staff|lead|head)\b", title_lower):
        return "lead" in levels
    if re.search(r"\bsenior\b|\bsr\.?\b", title_lower):
        return bool(levels & {"senior", "lead"})
    return True


def _freshness(posted_at: datetime | None) -> float:
    if not posted_at:
        return 0.5
    now = datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    hours = (now - posted_at).total_seconds() / 3600
    if hours <= 24:
        return 1.0
    if hours <= 72:
        return 0.7
    return 0.3


def _profile_text(profile: UserProfile, parsed: ParsedResume | None) -> str:
    """Scoring text for the profile. Contact details are deliberately excluded."""
    parts = [
        " ".join(profile.target_roles),
        " ".join(profile.skills_must_have),
        " ".join(profile.skills_nice_to_have),
        profile.current_role,
        profile.current_company,
        profile.industry,
    ]
    if parsed:
        parts.append(parsed.summary)
        parts.extend(parsed.skills_must_have)
        for exp in parsed.experience:
            parts.append(exp.role)
            parts.extend(exp.bullets)
    return " ".join(parts)


# Job boards use current city names while people still type the older ones.
CITY_ALIASES: dict[str, tuple[str, ...]] = {
    "bangalore": ("bengaluru",),
    "bengaluru": ("bangalore",),
    "bombay": ("mumbai",),
    "mumbai": ("bombay",),
    "calcutta": ("kolkata",),
    "kolkata": ("calcutta",),
    "madras": ("chennai",),
    "chennai": ("madras",),
    "gurgaon": ("gurugram",),
    "gurugram": ("gurgaon",),
    "poona": ("pune",),
    "pune": ("poona",),
    "trivandrum": ("thiruvananthapuram",),
    "thiruvananthapuram": ("trivandrum",),
    "delhi": ("new delhi", "ncr", "national capital region"),
}


def _location_variants(location: str) -> set[str]:
    base = location.strip().lower()
    variants = {base}
    variants.update(CITY_ALIASES.get(base, ()))
    return {v for v in variants if v}


def _matches_exclude_keyword(keyword: str, *haystacks: str) -> bool:
    """Whole-word match so 'sales' does not exclude 'Salesforce'."""
    pattern = re.compile(rf"(?<!\w){re.escape(keyword.strip().lower())}(?!\w)")
    return any(pattern.search(h) for h in haystacks)


def _passes_hard_filters(profile: UserProfile, job: JobPosting) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    jd_lower = job.jd_text.lower()
    title_lower = job.title.lower()

    for kw in profile.exclude_keywords:
        if kw.strip() and _matches_exclude_keyword(kw, jd_lower, title_lower):
            return False, [f"Excluded keyword: {kw}"]

    if profile.salary_min and job.salary_max and job.salary_max < profile.salary_min:
        return False, ["Salary below minimum"]

    required_years = _extract_required_years(job.jd_text)
    profile_years = profile.experience_years or 0
    if required_years is not None and required_years > profile_years:
        return False, [
            f"Requires {required_years}+ years; profile has {profile_years:g}"
        ]

    if not _title_level_allowed(profile, job.title):
        return False, [
            f"Seniority mismatch: {job.title} is outside selected levels"
        ]

    if profile.locations and job.location:
        job_loc = job.location.lower()
        loc_hit = any(
            variant in job_loc
            for loc in profile.locations
            for variant in _location_variants(loc)
        )
        modes = getattr(profile, "work_modes", None) or [
            getattr(profile, "work_mode", "any")
        ]
        normalized_modes = {getattr(mode, "value", mode) for mode in modes}
        remote_ok = bool(normalized_modes & {"remote", "any"}) and "remote" in job_loc
        if not loc_hit and not remote_ok:
            return False, [f"Location mismatch: {job.location}"]

    reasons.append("Passed hard filters")
    return True, reasons


def score_job(
    profile: UserProfile,
    job: JobPosting,
    parsed: ParsedResume | None,
) -> tuple[float, list[str]]:
    ok, filter_reasons = _passes_hard_filters(profile, job)
    if not ok:
        return 0.0, filter_reasons

    profile_skills = list(dict.fromkeys(profile.skills_must_have + profile.skills_nice_to_have))
    if parsed:
        profile_skills = list(dict.fromkeys(profile_skills + parsed.skills_must_have))

    semantic = _semantic_coverage(
        _profile_text(profile, parsed),
        f"{job.title} {job.jd_text}",
    )
    skill_score, skill_hits = _skill_overlap(profile_skills, job.jd_text)
    role_score, role_hits = _role_match(profile.target_roles, job.title, job.jd_text)
    exp_score = _exp_fit(profile, job.jd_text)
    fresh_score = _freshness(job.posted_at)

    final = (
        0.45 * semantic
        + 0.25 * skill_score
        + 0.15 * role_score
        + 0.10 * exp_score
        + 0.05 * fresh_score
    ) * 100

    reasons: list[str] = []
    if skill_hits:
        reasons.append(f"Skills matched: {', '.join(skill_hits[:5])}")
    if role_hits:
        reasons.append(f"Role matched: {', '.join(role_hits[:3])}")
    reasons.append(f"Semantic similarity: {semantic:.0%}")
    reasons.append(f"Experience fit: {exp_score:.0%}")
    if job.posted_at:
        reasons.append(f"Posted: {job.posted_at.strftime('%Y-%m-%d')}")

    return round(min(final, 100.0), 1), reasons[:5]
