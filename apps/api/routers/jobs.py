import sys
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import get_db
from deps import verify_worker_key
from models import JobMatch, JobPosting, ParsedResume, UserProfile
from packages.shared.schemas import JobBulkCreate, JobResponse
from services.match_engine import score_job

router = APIRouter(tags=["jobs"])


def _job_response(job: JobPosting, match: JobMatch | None = None) -> JobResponse:
    return JobResponse(
        id=job.id,
        source=job.source,
        external_id=job.external_id,
        title=job.title,
        company=job.company,
        location=job.location,
        jd_text=job.jd_text,
        posted_at=job.posted_at,
        url=job.url,
        created_at=job.created_at,
        match_score=match.score if match else None,
        match_reasons=match.reasons if match else [],
        match_id=match.id if match else None,
        match_status=match.status if match else None,
    )


@router.post("/jobs/bulk", dependencies=[Depends(verify_worker_key)])
def ingest_jobs_bulk(payload: JobBulkCreate, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    parsed_row = db.query(ParsedResume).filter(ParsedResume.profile_id == profile.id).first()
    parsed = None
    if parsed_row:
        from packages.shared.schemas import ParsedResume as ParsedResumeSchema
        parsed = ParsedResumeSchema.model_validate(parsed_row.json_blob)

    created = 0
    updated = 0
    matched = 0
    for job_data in payload.jobs[: profile.max_jobs_per_run]:
        existing = (
            db.query(JobPosting)
            .filter(JobPosting.source == job_data.source, JobPosting.external_id == job_data.external_id)
            .first()
        )
        jd_changed = False
        if existing:
            job = existing
            # An earlier run may have stored an empty or truncated description.
            if len(job_data.jd_text) > len(job.jd_text or ""):
                job.jd_text = job_data.jd_text
                job.raw_json = job_data.raw_json
                jd_changed = True
                updated += 1
        else:
            job = JobPosting(**job_data.model_dump())
            db.add(job)
            db.flush()
            created += 1

        match = db.query(JobMatch).filter(JobMatch.profile_id == profile.id, JobMatch.job_id == job.id).first()
        if match and not jd_changed:
            continue

        score, reasons = score_job(profile, job, parsed)
        if match:
            # Preserve a tailored/applied match; only refresh the score.
            match.score = score
            match.reasons = reasons
            if match.status in ("pending", "skipped"):
                match.status = "pending" if score >= profile.match_threshold else "skipped"
        else:
            status = "pending" if score >= profile.match_threshold else "skipped"
            match = JobMatch(profile_id=profile.id, job_id=job.id, score=score, reasons=reasons, status=status)
            db.add(match)
        if score >= profile.match_threshold:
            matched += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "matched_above_threshold": matched,
        "total_received": len(payload.jobs),
    }


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    profile_id: UUID = Query(...),
    min_score: float = Query(0),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(JobPosting, JobMatch)
        .join(JobMatch, JobMatch.job_id == JobPosting.id)
        .filter(JobMatch.profile_id == profile_id, JobMatch.score >= min_score)
        .order_by(JobMatch.score.desc())
        .all()
    )
    return [_job_response(job, match) for job, match in rows]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, profile_id: UUID = Query(...), db: Session = Depends(get_db)):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    match = db.query(JobMatch).filter(JobMatch.profile_id == profile_id, JobMatch.job_id == job_id).first()
    return _job_response(job, match)
