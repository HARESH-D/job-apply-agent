import sys
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.graphs.tailor_graph import run_tailor_pipeline
from config import settings
from database import get_db
from models import JobMatch, JobPosting, ParsedResume, TailoredResume, UserProfile
from packages.shared.schemas import JobResponse, MatchResponse, ParsedResume as ParsedResumeSchema, TailorResponse
from routers.jobs import _job_response
from services.rescoring import rescore_profile
from services.resume_renderer import render_ats_resume

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchResponse])
def list_matches(profile_id: UUID, min_score: float = 0, db: Session = Depends(get_db)):
    rows = (
        db.query(JobMatch)
        .filter(JobMatch.profile_id == profile_id, JobMatch.score >= min_score)
        .order_by(JobMatch.score.desc())
        .all()
    )
    result = []
    for m in rows:
        job = db.query(JobPosting).filter(JobPosting.id == m.job_id).first()
        result.append(MatchResponse(
            id=m.id,
            profile_id=m.profile_id,
            job_id=m.job_id,
            score=m.score,
            reasons=m.reasons or [],
            status=m.status,
            created_at=m.created_at,
            job=_job_response(job, m) if job else None,
        ))
    return result


@router.post("/rescore")
def rescore_matches(profile_id: UUID, db: Session = Depends(get_db)):
    """Recompute every match for a profile — used after tuning the threshold or
    when the scoring logic changes."""
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return rescore_profile(db, profile)


@router.post("/{match_id}/tailor", response_model=TailorResponse)
def tailor_resume(match_id: UUID, db: Session = Depends(get_db)):
    match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    parsed_row = db.query(ParsedResume).filter(ParsedResume.profile_id == match.profile_id).first()
    if not parsed_row:
        raise HTTPException(status_code=400, detail="Upload a base resume first")

    job = db.query(JobPosting).filter(JobPosting.id == match.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tailored_dict, diff_summary = run_tailor_pipeline(
        parsed_row.json_blob,
        job.jd_text,
        job.title,
    )
    tailored = ParsedResumeSchema.model_validate(tailored_dict)

    out_dir = Path(settings.storage_path) / "tailored" / str(match.profile_id)
    docx_path = out_dir / f"{match_id}.docx"
    render_ats_resume(tailored, docx_path)

    existing = db.query(TailoredResume).filter(TailoredResume.match_id == match_id).first()
    if existing:
        existing.docx_path = str(docx_path)
        existing.diff_summary = diff_summary
    else:
        db.add(TailoredResume(match_id=match_id, docx_path=str(docx_path), diff_summary=diff_summary))

    match.status = "tailored"
    db.commit()

    return TailorResponse(match_id=match_id, diff_summary=diff_summary, docx_path=str(docx_path), status="tailored")


@router.get("/{match_id}/resume")
def download_tailored_resume(match_id: UUID, db: Session = Depends(get_db)):
    row = db.query(TailoredResume).filter(TailoredResume.match_id == match_id).first()
    if not row or not Path(row.docx_path).exists():
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    return FileResponse(
        row.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"resume_{match_id}.docx",
    )
