"""Fact-bounded, JD-aware resume tailoring with optional Gemini rewriting."""
from __future__ import annotations

import re
from typing import Any

from packages.shared.schemas import ExperienceEntry, ParsedResume


JD_STOPWORDS = {
    "and", "the", "our", "you", "your", "for", "with", "will", "are", "this", "that",
    "have", "has", "from", "who", "they", "their", "not", "but", "all", "can", "any",
    "job", "role", "team", "work", "working", "years", "year", "experience", "ability",
    "strong", "good", "excellent", "including", "etc", "such", "other", "more", "new",
    "we", "us", "is", "be", "to", "of", "in", "on", "at", "as", "an", "or", "by", "it",
    "company", "candidate", "candidates", "position", "opportunity", "responsibilities",
    "requirements", "skills", "must", "should", "would", "about", "across", "within",
    "apply", "please", "join", "looking", "help", "make", "also", "well", "using", "use",
}
TECH_TERMS = {
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Python",
    "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js",
    "FastAPI", "Django", "Flask", "Spring", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "Kafka", "Git", "CI/CD", "REST", "GraphQL", "Linux", "SQL",
}


def _extract_jd_keywords(jd_text: str) -> list[str]:
    """Most frequent domain terms in the job description (stopwords removed)."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}", jd_text)
    freq: dict[str, int] = {}
    for t in tokens:
        low = t.lower().strip(".")
        if len(low) > 2 and low not in JD_STOPWORDS:
            freq[low] = freq.get(low, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:25]]


def extract_jd_requirements(
    jd_text: str, job_title: str, base_skills: list[str]
) -> dict[str, Any]:
    """Return structured, explainable JD requirements."""
    from services.match_engine import _extract_required_years

    matched = [
        skill
        for skill in base_skills
        if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", jd_text, re.IGNORECASE)
    ]
    mentioned_tech = [
        term
        for term in sorted(TECH_TERMS)
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", jd_text, re.IGNORECASE)
    ]
    matched_lower = {skill.lower() for skill in matched}
    gaps = [term for term in mentioned_tech if term.lower() not in matched_lower]
    return {
        "job_title": job_title,
        "experience_years": _extract_required_years(jd_text),
        "keywords": _extract_jd_keywords(f"{job_title} {jd_text}"),
        "matched_skills": matched,
        "skill_gaps": gaps,
    }


def _bullet_keyword_hits(bullet: str, keywords: list[str]) -> int:
    low = bullet.lower()
    return sum(1 for kw in keywords if kw in low)


def _reorder_bullets(bullets: list[str], keywords: list[str]) -> list[str]:
    """Surface JD-relevant bullets first; never rewrite or invent content."""
    return sorted(bullets, key=lambda b: -_bullet_keyword_hits(b, keywords))


def _reorder_skills(resume: ParsedResume, keywords: list[str]) -> list[str]:
    skills = list(dict.fromkeys(resume.skills_must_have + resume.skills_nice_to_have))

    def rank(s: str) -> int:
        s_low = s.lower()
        for i, kw in enumerate(keywords):
            if kw in s_low or s_low in kw:
                return i
        return 100 + skills.index(s)

    return sorted(skills, key=rank)


def _local_tailor(
    base: ParsedResume, requirements: dict[str, Any]
) -> ParsedResume:
    keywords = requirements["keywords"]

    tailored_exp: list[ExperienceEntry] = []
    for exp in base.experience:
        # Keep the original role verbatim — never substitute the target job title.
        tailored_exp.append(ExperienceEntry(
            company=exp.company,
            role=exp.role,
            start_date=exp.start_date,
            end_date=exp.end_date,
            bullets=_reorder_bullets(exp.bullets, keywords)[:7],
        ))

    ordered_skills = _reorder_skills(base, keywords)
    # Prefer the existing summary; only append a soft focus line that does not
    # claim the candidate already holds the target title.
    tailored = base.model_copy(deep=True)
    tailored.experience = tailored_exp
    tailored.skills_must_have = ordered_skills[:15]
    tailored.skills_nice_to_have = ordered_skills[15:]
    tailored.projects = sorted(
        base.projects,
        key=lambda project: -_bullet_keyword_hits(
            " ".join([project.name, project.description, *project.bullets]),
            keywords,
        ),
    )
    return tailored


def validate_tailored_resume(
    base: ParsedResume, tailored: ParsedResume
) -> list[str]:
    """Return factuality violations. An empty list means validation passed."""
    issues: list[str] = []

    base_companies = {e.company for e in base.experience if e.company}
    tailored_companies = {e.company for e in tailored.experience if e.company}
    if tailored_companies - base_companies:
        issues.append("Changed or invented companies")

    base_roles = {e.role.lower() for e in base.experience if e.role}
    tailored_roles = {e.role.lower() for e in tailored.experience if e.role}
    if tailored_roles - base_roles:
        issues.append("Changed or invented roles")

    base_skills = {s.lower() for s in base.skills_must_have + base.skills_nice_to_have}
    tailored_skills = {s.lower() for s in tailored.skills_must_have + tailored.skills_nice_to_have}
    invented_skills = tailored_skills - base_skills
    if invented_skills:
        issues.append(f"Invented skills: {', '.join(sorted(invented_skills))}")

    base_dates = {(e.start_date, e.end_date) for e in base.experience}
    tailored_dates = {(e.start_date, e.end_date) for e in tailored.experience}
    if not tailored_dates <= base_dates:
        issues.append("Changed or invented employment dates")

    base_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", " ".join(
        bullet for exp in base.experience for bullet in exp.bullets
    )))
    tailored_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", " ".join(
        bullet for exp in tailored.experience for bullet in exp.bullets
    )))
    if tailored_numbers - base_numbers:
        issues.append("Changed or invented metrics")

    leak_phrases = ("here is", "revised resume", "as an ai", "tailored resume")
    if any(phrase in tailored.summary.lower() for phrase in leak_phrases):
        issues.append("LLM meta-language leaked into resume")
    return issues


def run_tailor_pipeline(
    base_resume: dict,
    jd_text: str,
    job_title: str,
    *,
    use_gemini: bool = False,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-2.5-flash-lite",
) -> tuple[dict, str]:
    base = ParsedResume.model_validate(base_resume)
    skills = base.skills_must_have + base.skills_nice_to_have
    requirements = extract_jd_requirements(jd_text, job_title, skills)
    local = _local_tailor(base, requirements)
    tailored = local
    engine = "local fallback" if use_gemini else "local"

    if use_gemini and gemini_api_key:
        try:
            from services.gemini_tailor import rewrite_resume_with_gemini

            candidate = rewrite_resume_with_gemini(
                local, jd_text, requirements, gemini_api_key, gemini_model
            )
            if not validate_tailored_resume(base, candidate):
                tailored = candidate
                engine = "Gemini"
            else:
                engine = "local fallback"
        except Exception:
            engine = "local fallback"

    issues = validate_tailored_resume(base, tailored)
    if issues:
        tailored = local
        engine = "local fallback"

    parts = [
        f"Engine: {engine}",
        f"Reordered skills and bullets for {job_title}",
    ]
    if requirements["matched_skills"]:
        parts.append(
            "Matched: " + ", ".join(requirements["matched_skills"][:6])
        )
    if requirements["skill_gaps"]:
        parts.append("Skill gaps (not added): " + ", ".join(requirements["skill_gaps"][:6]))
    return tailored.model_dump(), "; ".join(parts)
