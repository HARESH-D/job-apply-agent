"""LangGraph resume tailoring pipeline with rule-based fallback.

Never invents companies, skills, or job titles that are not in the base resume.
Bullet text is reordered (not rewritten) so ATS output stays factually honest.
"""
from __future__ import annotations

import re
from typing import TypedDict

from packages.shared.schemas import ExperienceEntry, ParsedResume


class TailorState(TypedDict):
    base_resume: dict
    jd_text: str
    job_title: str
    tailored_resume: dict
    diff_summary: str
    qa_passed: bool
    retry_count: int


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


def _extract_jd_keywords(jd_text: str) -> list[str]:
    """Most frequent domain terms in the job description (stopwords removed)."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}", jd_text)
    freq: dict[str, int] = {}
    for t in tokens:
        low = t.lower().strip(".")
        if len(low) > 2 and low not in JD_STOPWORDS:
            freq[low] = freq.get(low, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:25]]


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


def tailor_node(state: TailorState) -> TailorState:
    base = ParsedResume.model_validate(state["base_resume"])
    keywords = _extract_jd_keywords(state["jd_text"] + " " + state["job_title"])

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
    summary = (base.summary or "").strip()
    title = state["job_title"].strip()
    if title and title.lower() not in summary.lower():
        focus = f"Targeting roles such as {title}."
        summary = f"{summary} {focus}".strip() if summary else focus

    tailored = base.model_copy(deep=True)
    tailored.experience = tailored_exp
    tailored.skills_must_have = ordered_skills[:15]
    tailored.skills_nice_to_have = ordered_skills[15:]
    tailored.summary = summary[:500]

    diff_parts = [
        f"Reordered skills toward keywords for {title or 'target role'}",
        "Reordered experience bullets by JD keyword overlap (content unchanged)",
    ]
    if title and title.lower() not in (base.summary or "").lower():
        diff_parts.append(f"Noted target role focus: {title}")
    if keywords:
        diff_parts.append(f"Top JD terms used for ordering: {', '.join(keywords[:5])}")

    return {
        **state,
        "tailored_resume": tailored.model_dump(),
        "diff_summary": "; ".join(diff_parts),
        "qa_passed": False,
    }


def qa_node(state: TailorState) -> TailorState:
    base = ParsedResume.model_validate(state["base_resume"])
    tailored = ParsedResume.model_validate(state["tailored_resume"])

    base_companies = {e.company for e in base.experience if e.company}
    tailored_companies = {e.company for e in tailored.experience if e.company}
    invented_companies = tailored_companies - base_companies

    base_roles = {e.role.lower() for e in base.experience if e.role}
    tailored_roles = {e.role.lower() for e in tailored.experience if e.role}
    invented_roles = tailored_roles - base_roles

    base_skills = {s.lower() for s in base.skills_must_have + base.skills_nice_to_have}
    tailored_skills = {s.lower() for s in tailored.skills_must_have + tailored.skills_nice_to_have}
    invented_skills = tailored_skills - base_skills

    # Reject soft title invention patterns from older tailor versions.
    summary_low = tailored.summary.lower()
    fabricated_title_claim = bool(
        state["job_title"]
        and f"{state['job_title'].lower()} professional" in summary_low
        and state["job_title"].lower() not in (base.summary or "").lower()
    )

    passed = (
        not invented_companies
        and not invented_roles
        and not invented_skills
        and not fabricated_title_claim
        and len(tailored.summary) <= 600
    )
    return {**state, "qa_passed": passed, "retry_count": state["retry_count"] + 1}


def run_tailor_pipeline(base_resume: dict, jd_text: str, job_title: str) -> tuple[dict, str]:
    state: TailorState = {
        "base_resume": base_resume,
        "jd_text": jd_text,
        "job_title": job_title,
        "tailored_resume": {},
        "diff_summary": "",
        "qa_passed": False,
        "retry_count": 0,
    }

    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(TailorState)
        graph.add_node("tailor", tailor_node)
        graph.add_node("qa", qa_node)

        def route_after_qa(s: TailorState):
            if s["qa_passed"] or s["retry_count"] >= 1:
                return END
            return "tailor"

        graph.set_entry_point("tailor")
        graph.add_edge("tailor", "qa")
        graph.add_conditional_edges("qa", route_after_qa, {"tailor": "tailor", END: END})
        app = graph.compile()
        result = app.invoke(state)
        return result["tailored_resume"], result["diff_summary"]
    except Exception:
        state = tailor_node(state)
        state = qa_node(state)
        return state["tailored_resume"], state["diff_summary"]
