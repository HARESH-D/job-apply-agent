"""Recompute stored match scores for a profile."""
from sqlalchemy.orm import Session

from models import JobMatch, JobPosting, ParsedResume, UserProfile
from packages.shared.schemas import ParsedResume as ParsedResumeSchema
from services.match_engine import score_job


def rescore_profile(db: Session, profile: UserProfile) -> dict[str, float | int]:
    """Re-score every match for a profile.

    Called whenever an input to scoring changes: the profile fields, the match
    threshold, or the uploaded resume. Matches already tailored or applied keep
    their status so user work is never lost.
    """
    parsed_row = db.query(ParsedResume).filter(ParsedResume.profile_id == profile.id).first()
    parsed = ParsedResumeSchema.model_validate(parsed_row.json_blob) if parsed_row else None

    matches = db.query(JobMatch).filter(JobMatch.profile_id == profile.id).all()
    above = 0
    for match in matches:
        job = db.query(JobPosting).filter(JobPosting.id == match.job_id).first()
        if not job:
            continue
        score, reasons = score_job(profile, job, parsed)
        match.score = score
        match.reasons = reasons
        if match.status in ("pending", "skipped"):
            match.status = "pending" if score >= profile.match_threshold else "skipped"
        if score >= profile.match_threshold:
            above += 1

    db.commit()
    return {
        "rescored": len(matches),
        "above_threshold": above,
        "threshold": profile.match_threshold,
    }
