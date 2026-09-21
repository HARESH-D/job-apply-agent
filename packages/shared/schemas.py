"""Shared Pydantic schemas for API, worker, and agents."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class SeniorityLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    ANY = "any"


class CompanySize(str, Enum):
    STARTUP = "startup"
    MID = "mid"
    ENTERPRISE = "enterprise"
    ANY = "any"


class MatchStatus(str, Enum):
    PENDING = "pending"
    TAILORED = "tailored"
    APPLIED = "applied"
    SKIPPED = "skipped"


class ScrapeRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CAPTCHA = "captcha"


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ExperienceEntry(BaseModel):
    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = "present"
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str = ""
    degree: str = ""
    year: str = ""


class ParsedResume(BaseModel):
    name: str = ""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    skills_must_have: list[str] = Field(default_factory=list)
    skills_nice_to_have: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ProfileCreate(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    skills_must_have: list[str] = Field(default_factory=list)
    skills_nice_to_have: list[str] = Field(default_factory=list)
    experience_years: float = 0
    seniority_level: SeniorityLevel = SeniorityLevel.MID
    locations: list[str] = Field(default_factory=list)
    work_mode: WorkMode = WorkMode.ANY
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    current_role: str = ""
    current_company: str = ""
    industry: str = ""
    work_authorization: str = ""
    willing_to_relocate: bool = False
    relocate_cities: list[str] = Field(default_factory=list)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    exclude_keywords: list[str] = Field(default_factory=list)
    industry_preferences: list[str] = Field(default_factory=list)
    company_size: CompanySize = CompanySize.ANY
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    notice_period_days: Optional[int] = None
    earliest_start_date: Optional[str] = None
    max_jobs_per_run: int = 50
    match_threshold: float = 50.0
    contact: ContactInfo = Field(default_factory=ContactInfo)


class ProfileResponse(ProfileCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    has_resume: bool = False


class JobPostingCreate(BaseModel):
    source: str = "linkedin"
    external_id: str
    title: str
    company: str
    location: str = ""
    jd_text: str = ""
    posted_at: Optional[datetime] = None
    url: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class JobBulkCreate(BaseModel):
    profile_id: UUID
    jobs: list[JobPostingCreate]


class JobResponse(BaseModel):
    id: UUID
    source: str
    external_id: str
    title: str
    company: str
    location: str
    jd_text: str
    posted_at: Optional[datetime]
    url: str
    created_at: datetime
    match_score: Optional[float] = None
    match_reasons: list[str] = Field(default_factory=list)
    match_id: Optional[UUID] = None
    match_status: Optional[MatchStatus] = None


class MatchResponse(BaseModel):
    id: UUID
    profile_id: UUID
    job_id: UUID
    score: float
    reasons: list[str]
    status: MatchStatus
    created_at: datetime
    job: Optional[JobResponse] = None


class ScrapeRunCreate(BaseModel):
    profile_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    jobs_found: int = 0
    errors: str = ""
    status: ScrapeRunStatus = ScrapeRunStatus.RUNNING


class ScrapeRunResponse(ScrapeRunCreate):
    id: UUID


class TailorResponse(BaseModel):
    match_id: UUID
    diff_summary: str
    docx_path: str
    status: MatchStatus


class ActiveProfileConfig(BaseModel):
    profile: ProfileResponse
    search_urls: list[str]
