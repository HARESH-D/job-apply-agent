import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid():
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    target_roles: Mapped[list] = mapped_column(JSON, default=list)
    skills_must_have: Mapped[list] = mapped_column(JSON, default=list)
    skills_nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    seniority_levels: Mapped[list] = mapped_column(JSON, default=lambda: ["mid"])
    work_modes: Mapped[list] = mapped_column(JSON, default=lambda: ["any"])
    # Legacy singular columns are kept for backward-compatible migration.
    seniority_level: Mapped[str] = mapped_column(String(32), default="mid")
    locations: Mapped[list] = mapped_column(JSON, default=list)
    work_mode: Mapped[str] = mapped_column(String(32), default="any")
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="USD")
    current_role: Mapped[str] = mapped_column(String(256), default="")
    current_company: Mapped[str] = mapped_column(String(256), default="")
    industry: Mapped[str] = mapped_column(String(256), default="")
    work_authorization: Mapped[str] = mapped_column(String(128), default="")
    willing_to_relocate: Mapped[bool] = mapped_column(default=False)
    relocate_cities: Mapped[list] = mapped_column(JSON, default=list)
    employment_type: Mapped[str] = mapped_column(String(32), default="full_time")
    exclude_keywords: Mapped[list] = mapped_column(JSON, default=list)
    industry_preferences: Mapped[list] = mapped_column(JSON, default=list)
    company_size: Mapped[str] = mapped_column(String(32), default="any")
    education: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earliest_start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_jobs_per_run: Mapped[int] = mapped_column(Integer, default=50)
    match_threshold: Mapped[float] = mapped_column(Float, default=50.0)
    contact: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    parsed_resume: Mapped["ParsedResume | None"] = relationship(back_populates="profile", uselist=False)
    matches: Mapped[list["JobMatch"]] = relationship(back_populates="profile")
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="profile")


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), unique=True)
    json_blob: Mapped[dict] = mapped_column(JSON, default=dict)
    source_file_path: Mapped[str] = mapped_column(String(512), default="")
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    profile: Mapped["UserProfile"] = relationship(back_populates="parsed_resume")


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), default="linkedin")
    external_id: Mapped[str] = mapped_column(String(256))
    title: Mapped[str] = mapped_column(String(512))
    company: Mapped[str] = mapped_column(String(256))
    location: Mapped[str] = mapped_column(String(256), default="")
    jd_text: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    url: Mapped[str] = mapped_column(String(1024), default="")
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    jd_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    matches: Mapped[list["JobMatch"]] = relationship(back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("profile_id", "job_id", name="uq_profile_job"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_postings.id"))
    score: Mapped[float] = mapped_column(Float, default=0)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    profile: Mapped["UserProfile"] = relationship(back_populates="matches")
    job: Mapped["JobPosting"] = relationship(back_populates="matches")
    tailored_resume: Mapped["TailoredResume | None"] = relationship(back_populates="match", uselist=False)


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_matches.id"), unique=True)
    docx_path: Mapped[str] = mapped_column(String(512))
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    diff_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    match: Mapped["JobMatch"] = relationship(back_populates="tailored_resume")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="running")

    profile: Mapped["UserProfile"] = relationship(back_populates="scrape_runs")
