"""Merge user-owned factual profile data into a parsed base resume."""
from packages.shared.schemas import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    ParsedResume,
)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def merge_resume_facts(profile, parsed: ParsedResume) -> ParsedResume:
    """Fill parsed-resume gaps from fields explicitly saved by the user."""
    merged = parsed.model_copy(deep=True)
    contact = profile.contact or {}
    base_contact = merged.contact.model_dump()
    for field in ("email", "phone", "linkedin", "github", "portfolio"):
        if contact.get(field):
            base_contact[field] = contact[field]
    merged.contact = ContactInfo.model_validate(base_contact)

    if not merged.location:
        merged.location = next(
            (
                location
                for location in (profile.locations or [])
                if location.lower() != "remote"
            ),
            "",
        )

    merged.skills_must_have = _dedupe(
        merged.skills_must_have + (profile.skills_must_have or [])
    )
    merged.skills_nice_to_have = _dedupe(
        merged.skills_nice_to_have + (profile.skills_nice_to_have or [])
    )

    if profile.education:
        merged.education = [
            EducationEntry.model_validate(item) for item in profile.education
        ]
    merged.certifications = _dedupe(
        merged.certifications + (profile.certifications or [])
    )

    if (
        not merged.experience
        and (profile.current_role or profile.current_company)
    ):
        merged.experience = [
            ExperienceEntry(
                role=profile.current_role or "",
                company=profile.current_company or "",
                bullets=[],
            )
        ]
    return merged
