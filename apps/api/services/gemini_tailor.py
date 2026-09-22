"""Opt-in Gemini resume rewrite. Callers must obtain explicit user consent."""
import json

import httpx

from packages.shared.schemas import ParsedResume


def rewrite_resume_with_gemini(
    resume: ParsedResume,
    jd_text: str,
    requirements: dict,
    api_key: str,
    model: str,
) -> ParsedResume:
    prompt = f"""
Rewrite this resume for the job description using only facts already present.
Return JSON matching the input resume shape.

Rules:
- Never add skills, employers, roles, dates, degrees, certifications, projects,
  metrics, responsibilities, or achievements.
- Keep company names, role titles, dates, and all numbers exactly unchanged.
- You may reorder sections and bullets and rephrase a bullet only when its
  factual meaning is unchanged.
- Keep the summary concise and do not claim the target title as a past role.
- Missing job skills must remain missing.
- Return JSON only, with no markdown or commentary.

JD requirements:
{json.dumps(requirements, ensure_ascii=False)}

Job description:
{jd_text[:12000]}

Verified base resume:
{resume.model_dump_json()}
""".strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    response = httpx.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=45.0,
    )
    response.raise_for_status()
    body = response.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    return ParsedResume.model_validate_json(text)
