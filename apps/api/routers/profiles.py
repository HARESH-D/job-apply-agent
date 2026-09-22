import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from database import get_db
from deps import verify_worker_key
from models import ParsedResume, UserProfile
from packages.shared.schemas import (
    ActiveProfileConfig,
    ParsedResume as ParsedResumeSchema,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from services.rescoring import rescore_profile
from services.resume_parser import parse_resume_file
from services.search_builder import build_linkedin_search_urls

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _to_response(profile: UserProfile, db: Session) -> ProfileResponse:
    has_resume = db.query(ParsedResume).filter(ParsedResume.profile_id == profile.id).first() is not None
    return ProfileResponse(
        id=profile.id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        has_resume=has_resume,
        target_roles=profile.target_roles or [],
        skills_must_have=profile.skills_must_have or [],
        skills_nice_to_have=profile.skills_nice_to_have or [],
        experience_years=profile.experience_years,
        seniority_levels=profile.seniority_levels
        or [profile.seniority_level or "mid"],
        seniority_level=profile.seniority_level,
        locations=profile.locations or [],
        work_modes=profile.work_modes or [profile.work_mode or "any"],
        work_mode=profile.work_mode,
        salary_min=profile.salary_min,
        salary_max=profile.salary_max,
        salary_currency=profile.salary_currency,
        current_role=profile.current_role,
        current_company=profile.current_company,
        industry=profile.industry,
        work_authorization=profile.work_authorization,
        willing_to_relocate=profile.willing_to_relocate,
        relocate_cities=profile.relocate_cities or [],
        employment_type=profile.employment_type,
        exclude_keywords=profile.exclude_keywords or [],
        industry_preferences=profile.industry_preferences or [],
        company_size=profile.company_size,
        education=profile.education or [],
        certifications=profile.certifications or [],
        notice_period_days=profile.notice_period_days,
        earliest_start_date=profile.earliest_start_date,
        max_jobs_per_run=profile.max_jobs_per_run,
        match_threshold=profile.match_threshold,
        contact=profile.contact or {},
    )


def _apply_profile_data(
    profile: UserProfile, data: ProfileCreate | ProfileUpdate
) -> None:
    values = data.model_dump(exclude_unset=isinstance(data, ProfileUpdate))
    for field, value in values.items():
        if value is None:
            continue
        setattr(profile, field, value)
    if "seniority_levels" in values and values["seniority_levels"]:
        profile.seniority_level = values["seniority_levels"][0]
    if "work_modes" in values and values["work_modes"]:
        profile.work_mode = values["work_modes"][0]
    profile.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("", response_model=ProfileResponse)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    profile = UserProfile()
    _apply_profile_data(profile, data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_response(profile, db)


@router.get("/active", response_model=ActiveProfileConfig, dependencies=[Depends(verify_worker_key)])
def get_active_profile(db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.is_active.is_(True)).order_by(UserProfile.updated_at.desc()).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile")
    return ActiveProfileConfig(
        profile=_to_response(profile, db),
        search_urls=build_linkedin_search_urls(profile),
    )


@router.get("/current", response_model=ProfileResponse)
def get_current_profile(db: Session = Depends(get_db)):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.is_active.is_(True))
        .order_by(UserProfile.updated_at.desc())
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile")
    return _to_response(profile, db)


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _to_response(profile, db)


@router.patch("/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: UUID, data: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    _apply_profile_data(profile, data)
    db.commit()
    db.refresh(profile)
    # Roles, skills and threshold all feed scoring, so stored matches are now stale.
    rescore_profile(db, profile)
    return _to_response(profile, db)


@router.put("/{profile_id}", response_model=ProfileResponse)
def replace_profile(profile_id: UUID, data: ProfileCreate, db: Session = Depends(get_db)):
    """Backward-compatible full update; new clients should use PATCH."""
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    _apply_profile_data(profile, data)
    db.commit()
    db.refresh(profile)
    rescore_profile(db, profile)
    return _to_response(profile, db)


@router.post("/{profile_id}/resume", response_model=ParsedResumeSchema)
async def upload_resume(profile_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    storage = Path(settings.storage_path) / "resumes" / str(profile_id)
    storage.mkdir(parents=True, exist_ok=True)
    # Never trust client paths — basename only, reject empty / traversal names.
    raw_name = Path(file.filename or "").name
    if not raw_name or raw_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    suffix = Path(raw_name).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx resumes are supported")
    dest = storage / raw_name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10 MB)")
    dest.write_bytes(content)

    parsed = parse_resume_file(dest, profile_skills=profile.skills_must_have)
    if profile.skills_must_have and not parsed.skills_must_have:
        parsed.skills_must_have = profile.skills_must_have

    existing = db.query(ParsedResume).filter(ParsedResume.profile_id == profile_id).first()
    if existing:
        existing.json_blob = parsed.model_dump()
        existing.source_file_path = str(dest)
        existing.parsed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        db.add(ParsedResume(
            profile_id=profile_id,
            json_blob=parsed.model_dump(),
            source_file_path=str(dest),
        ))
    db.commit()
    # A new resume changes every score, so refresh matches immediately.
    rescore_profile(db, profile)
    return parsed


@router.get("/{profile_id}/resume/parsed", response_model=ParsedResumeSchema)
def get_parsed_resume(profile_id: UUID, db: Session = Depends(get_db)):
    row = db.query(ParsedResume).filter(ParsedResume.profile_id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No parsed resume")
    return ParsedResumeSchema.model_validate(row.json_blob)
