from services.resume_parser import parse_resume_text
from services.gemini_resume_parser import validate_extracted_facts


RESUME_TEXT = """
Ada Example
ada@example.com | +1 555 0100 | linkedin.com/in/ada | ada.dev

PROFESSIONAL SUMMARY
Backend engineer building reliable services.

TECHNICAL SKILLS
Python, FastAPI, PostgreSQL, Docker

PROFESSIONAL EXPERIENCE
Software Engineer
Acme Corporation
Jan 2022 - Present
- Built Python APIs serving 20,000 requests per day.
- Reduced database latency by 30%.

EDUCATION
BSc Computer Science | Example University | 2022

PROJECTS
Forecasting Platform | Python, FastAPI
- Built a demand forecasting API.

CERTIFICATIONS
AWS Developer Associate
"""


def test_parse_resume_text_handles_multiline_facts():
    parsed = parse_resume_text(RESUME_TEXT)

    assert parsed.name == "Ada Example"
    assert parsed.contact.email == "ada@example.com"
    assert parsed.contact.linkedin == "linkedin.com/in/ada"
    assert parsed.contact.portfolio == "ada.dev"
    assert parsed.experience[0].role == "Software Engineer"
    assert parsed.experience[0].company == "Acme Corporation"
    assert parsed.experience[0].start_date == "Jan 2022"
    assert parsed.experience[0].end_date == "Present"
    assert len(parsed.experience[0].bullets) == 2
    assert parsed.education[0].degree == "BSc Computer Science"
    assert parsed.education[0].institution == "Example University"
    assert parsed.education[0].year == "2022"
    assert parsed.projects[0].name == "Forecasting Platform"
    assert parsed.projects[0].technologies == ["Python", "FastAPI"]


def test_parser_does_not_turn_short_bullets_into_new_jobs():
    parsed = parse_resume_text(
        """
Ada Example
EXPERIENCE
Engineer | Acme | 2023 - Present
- Improved reliability.
- Led releases.
"""
    )

    assert len(parsed.experience) == 1
    assert parsed.experience[0].bullets == [
        "Improved reliability.",
        "Led releases.",
    ]


def test_gemini_extraction_validator_rejects_invented_facts():
    parsed = parse_resume_text(RESUME_TEXT)
    parsed.experience[0].company = "Invented Corporation"

    missing = validate_extracted_facts(parsed, RESUME_TEXT)

    assert "Invented Corporation" in missing
