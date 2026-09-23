"""Optional consent-gated Gemini repair for locally parsed resumes."""
import json
import re

import httpx

from packages.shared.schemas import ParsedResume


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def validate_extracted_facts(candidate: ParsedResume, raw_text: str) -> list[str]:
    source = _normalized(raw_text)
    values = [
        candidate.name,
        candidate.contact.email or "",
        candidate.contact.phone or "",
        candidate.contact.linkedin or "",
        candidate.contact.github or "",
        candidate.contact.portfolio or "",
        *candidate.skills_must_have,
        *candidate.skills_nice_to_have,
        *candidate.certifications,
    ]
    for entry in candidate.experience:
        values.extend([entry.company, entry.role, entry.start_date, entry.end_date])
    for entry in candidate.education:
        values.extend([entry.degree, entry.institution, entry.year])
    for project in candidate.projects:
        values.extend([project.name, *project.technologies])

    missing = []
    for value in values:
        normalized = _normalized(value)
        if normalized and normalized not in source:
            missing.append(value)
    return list(dict.fromkeys(missing))


def repair_resume_with_gemini(
    local: ParsedResume,
    raw_text: str,
    api_key: str,
    model: str,
) -> ParsedResume:
    prompt = f"""
Extract this resume into the supplied JSON schema.
Use only facts explicitly present in the raw resume. Do not infer or invent.
Repair section boundaries, multiline roles/companies/dates, education, contact
links, projects, technologies, certifications and achievements.
Return JSON only and preserve the schema exactly.

Local extraction to repair:
{local.model_dump_json()}

Raw resume:
{raw_text[:18000]}
""".strip()
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0,
            },
        },
        timeout=45.0,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    candidate = ParsedResume.model_validate_json(text)
    missing = validate_extracted_facts(candidate, raw_text)
    if missing:
        raise ValueError(
            "Gemini extraction introduced unverified facts: "
            + json.dumps(missing[:10])
        )
    candidate.extraction_warnings = []
    return candidate
