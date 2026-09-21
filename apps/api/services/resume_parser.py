"""Parse PDF/DOCX resumes into structured JSON."""
import re
from pathlib import Path

import pdfplumber
from docx import Document

from packages.shared.schemas import ContactInfo, EducationEntry, ExperienceEntry, ParsedResume

SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "experience": ("WORKEXPERIENCE", "PROFESSIONALEXPERIENCE", "EXPERIENCE", "EMPLOYMENT", "CAREERHISTORY"),
    "skills": ("TECHNICALSKILLS", "CORESKILLS", "SKILLS", "TECHNOLOGIES", "TECHSTACK"),
    "education": ("EDUCATION", "ACADEMIC", "QUALIFICATIONS"),
    "certifications": ("CERTIFICATIONS", "CERTIFICATION", "LICENSES"),
    "projects": ("PROJECTS", "PERSONALPROJECTS"),
    "summary": ("SUMMARY", "PROFESSIONALSUMMARY", "OBJECTIVE", "PROFILE", "ABOUTME"),
}

BULLET_PREFIX = re.compile(r"^\s*[-•*▪◦‣·]\s*|^\s*\d+[.)]\s*")
DATE_RANGE = re.compile(
    r"(19|20)\d{2}\s*[-–—to]+\s*((19|20)\d{2}|present|current)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")
URL_RE = re.compile(r"(https?://\S+|(?:www\.|linkedin\.com/|github\.com/)\S+)", re.IGNORECASE)


def _extract_text_pdf(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_text_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_pdf(path)
    if suffix == ".docx":
        return _extract_text_docx(path)
    if suffix == ".doc":
        raise ValueError("Legacy .doc is not supported — save as .docx or PDF")
    raise ValueError(f"Unsupported file type: {suffix}")


def _normalize_line(line: str) -> str:
    """Collapse letter-spaced text that PDF extraction produces.

    Designers often track out headings, so pdfplumber yields
    'W O R K   E X P E R I E N C E' instead of 'WORK EXPERIENCE'.
    """
    stripped = line.strip()
    tokens = stripped.split()
    if len(tokens) < 3:
        return stripped
    single_char = sum(1 for t in tokens if len(t) == 1)
    if single_char / len(tokens) < 0.6:
        return stripped
    words = [re.sub(r"\s+", "", w) for w in re.split(r"\s{2,}", stripped)]
    return " ".join(w for w in words if w)


def _heading_section(line: str) -> str | None:
    if len(line.split()) > 6 or not line.strip():
        return None
    key = re.sub(r"[^A-Za-z]", "", line).upper()
    if not key or len(key) > 40:
        return None
    for section, names in SECTION_KEYWORDS.items():
        for name in names:
            if key == name or (key.startswith(name) and len(key) <= len(name) + 4):
                return section
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {k: [] for k in SECTION_KEYWORDS}
    sections["header"] = []
    current = "header"
    for line in lines:
        section = _heading_section(line)
        if section:
            current = section
            continue
        sections[current].append(line)
    return sections


def _is_contact_line(line: str) -> bool:
    return bool(EMAIL_RE.search(line) or URL_RE.search(line)) or bool(
        PHONE_RE.search(line) and len(line) < 60
    )


def _parse_skills(lines: list[str], text: str, profile_skills: list[str] | None) -> list[str]:
    found: list[str] = []
    if profile_skills:
        lower = text.lower()
        found.extend(s for s in profile_skills if s.lower() in lower)
    for line in lines:
        cleaned = BULLET_PREFIX.sub("", line)
        for piece in re.split(r"[,;|•·/]| {2,}", cleaned):
            piece = piece.strip(" .:-")
            if 1 < len(piece) <= 30 and not piece.isdigit():
                found.append(piece)
    deduped: list[str] = []
    seen: set[str] = set()
    for skill in found:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(skill)
    return deduped[:40]


def _parse_experience(lines: list[str]) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    current: ExperienceEntry | None = None

    for line in lines:
        if not line.strip():
            continue
        is_bullet = bool(BULLET_PREFIX.match(line))
        text = BULLET_PREFIX.sub("", line).strip()
        if not text:
            continue

        date_match = DATE_RANGE.search(text)
        starts_entry = bool(date_match) or (
            not is_bullet and len(text.split()) <= 10 and not text.endswith(".")
        )

        if starts_entry and (current is None or current.bullets or date_match):
            role_line = DATE_RANGE.sub("", text).strip(" |,-–—")
            role, _, company = role_line.partition(" at ")
            if not company:
                parts = re.split(r"\s[|–—-]\s", role_line, maxsplit=1)
                role = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else ""
            start_date = end_date = ""
            if date_match:
                span = date_match.group(0)
                bits = re.split(r"[-–—]|to", span, maxsplit=1)
                start_date = bits[0].strip()
                end_date = bits[1].strip() if len(bits) > 1 else ""
            current = ExperienceEntry(
                company=company.strip(),
                role=role.strip(),
                start_date=start_date,
                end_date=end_date or "present",
                bullets=[],
            )
            entries.append(current)
            continue

        if current is None:
            current = ExperienceEntry(company="", role="", bullets=[])
            entries.append(current)
        if len(text) > 15:
            current.bullets.append(text)

    return [e for e in entries if e.bullets or e.role][:8]


def _parse_education(lines: list[str]) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    for line in lines:
        text = BULLET_PREFIX.sub("", line).strip()
        if len(text) < 4:
            continue
        year = ""
        year_match = re.search(r"(19|20)\d{2}", text)
        if year_match:
            year = year_match.group(0)
        entries.append(EducationEntry(institution=text, degree="", year=year))
        if len(entries) >= 5:
            break
    return entries


def _guess_name(header_lines: list[str]) -> str:
    for line in header_lines[:6]:
        clean = line.strip()
        if not clean or _is_contact_line(clean):
            continue
        if 1 <= len(clean.split()) <= 5 and not clean.isupper():
            return clean
        if 1 <= len(clean.split()) <= 5:
            return clean.title()
    return ""


def _build_summary(sections: dict[str, list[str]]) -> str:
    candidates = sections.get("summary") or []
    if not candidates:
        candidates = [
            l for l in sections.get("header", [])
            if len(l.split()) > 8 and not _is_contact_line(l)
        ]
    text = " ".join(l.strip() for l in candidates if not _is_contact_line(l))
    return re.sub(r"\s+", " ", text).strip()[:800]


def parse_resume_file(path: Path, profile_skills: list[str] | None = None) -> ParsedResume:
    raw = extract_text(path)
    lines = [_normalize_line(l) for l in raw.splitlines()]
    lines = [l for l in lines if l.strip()]
    normalized_text = "\n".join(lines)
    sections = _split_sections(lines)

    email = EMAIL_RE.search(normalized_text)
    phone = PHONE_RE.search(normalized_text)
    urls = URL_RE.findall(normalized_text)
    url_list = [u[0] if isinstance(u, tuple) else u for u in urls]
    linkedin = next((u for u in url_list if "linkedin" in u.lower()), None)
    github = next((u for u in url_list if "github" in u.lower()), None)

    experience = _parse_experience(sections["experience"])
    if not experience and sections["projects"]:
        experience = _parse_experience(sections["projects"])

    skills = _parse_skills(sections["skills"], normalized_text, profile_skills)

    return ParsedResume(
        name=_guess_name(sections["header"]),
        contact=ContactInfo(
            email=email.group(0) if email else "",
            phone=phone.group(0).strip() if phone else "",
            linkedin=linkedin,
            github=github,
        ),
        summary=_build_summary(sections),
        skills_must_have=skills,
        skills_nice_to_have=[],
        experience=experience,
        education=_parse_education(sections["education"]),
        certifications=[
            BULLET_PREFIX.sub("", l).strip() for l in sections["certifications"][:10] if len(l.strip()) > 3
        ],
    )
