"""ATS-friendly DOCX resume renderer."""
from pathlib import Path

from docx import Document
from docx.shared import Pt

from packages.shared.schemas import ParsedResume


def render_ats_resume(data: ParsedResume, output_path: Path) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    if data.name:
        p = doc.add_paragraph()
        run = p.add_run(data.name)
        run.bold = True
        run.font.size = Pt(14)

    contact_bits = [
        data.contact.email,
        data.contact.phone,
        data.contact.linkedin,
        data.contact.github,
    ]
    contact_line = " | ".join(c for c in contact_bits if c)
    if contact_line:
        doc.add_paragraph(contact_line)

    if data.summary:
        doc.add_heading("Summary", level=1)
        doc.add_paragraph(data.summary)

    all_skills = list(dict.fromkeys(data.skills_must_have + data.skills_nice_to_have))
    if all_skills:
        doc.add_heading("Skills", level=1)
        doc.add_paragraph(", ".join(all_skills))

    if data.experience:
        doc.add_heading("Experience", level=1)
        for exp in data.experience:
            header = " — ".join(p for p in [exp.role, exp.company] if p)
            if header:
                p = doc.add_paragraph()
                run = p.add_run(header)
                run.bold = True
            dates = " - ".join(p for p in [exp.start_date, exp.end_date] if p)
            if dates:
                doc.add_paragraph(dates)
            for bullet in exp.bullets:
                doc.add_paragraph(bullet, style="List Bullet")

    if data.education:
        doc.add_heading("Education", level=1)
        for edu in data.education:
            line = ", ".join(p for p in [edu.degree, edu.institution, edu.year] if p)
            if line:
                doc.add_paragraph(line)

    if data.certifications:
        doc.add_heading("Certifications", level=1)
        for cert in data.certifications:
            doc.add_paragraph(cert, style="List Bullet")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
