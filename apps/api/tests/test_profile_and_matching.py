import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import database
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from config import ROOT, resolve_database_url, resolve_storage_path
from models import Base, JobPosting, UserProfile
from packages.shared.schemas import ProfileCreate, ProfileUpdate
from routers.profiles import _apply_profile_data, get_current_profile
from services.match_engine import _extract_required_years, score_job
from services.search_builder import build_linkedin_search_urls


def test_relative_sqlite_and_storage_paths_resolve_from_repo_root():
    db_url = resolve_database_url("sqlite:///./jobagent.db")
    storage = resolve_storage_path("./storage")

    assert db_url == f"sqlite:///{(ROOT / 'jobagent.db').as_posix()}"
    assert storage == str((ROOT / "storage").resolve())


def test_legacy_sqlite_file_is_copied_once_to_stable_location(tmp_path):
    legacy = tmp_path / "legacy" / "jobagent.db"
    stable = tmp_path / "stable" / "jobagent.db"
    legacy.parent.mkdir()
    legacy.write_bytes(b"existing-profile-data")

    migrated = database._migrate_legacy_sqlite_file(
        f"sqlite:///{stable.as_posix()}", [legacy]
    )

    assert migrated is True
    assert stable.read_bytes() == b"existing-profile-data"
    legacy.write_bytes(b"do-not-overwrite-stable")
    assert database._migrate_legacy_sqlite_file(
        f"sqlite:///{stable.as_posix()}", [legacy]
    ) is False
    assert stable.read_bytes() == b"existing-profile-data"


def test_profile_accepts_multiple_seniority_levels_and_work_modes():
    profile = ProfileCreate(
        seniority_levels=["entry", "mid"],
        work_modes=["remote", "hybrid"],
    )

    assert [level.value for level in profile.seniority_levels] == ["entry", "mid"]
    assert [mode.value for mode in profile.work_modes] == ["remote", "hybrid"]


def test_search_builder_emits_combined_linkedin_filters():
    profile = SimpleNamespace(
        target_roles=["Software Engineer"],
        locations=["Bangalore"],
        seniority_levels=["entry", "mid"],
        work_modes=["remote", "hybrid"],
    )

    url = build_linkedin_search_urls(profile)[0]

    assert "f_E=2%2C3" in url
    assert "f_WT=2%2C3" in url


def test_required_years_parser_handles_common_ranges():
    assert _extract_required_years("Requires 6+ years of Python experience") == 6
    assert _extract_required_years("You have 5-7 years of experience") == 5
    assert _extract_required_years("Minimum 4 years in backend systems") == 4


def test_two_year_profile_rejects_six_year_job():
    profile = UserProfile(
        target_roles=["Software Engineer"],
        skills_must_have=["Python"],
        experience_years=2,
        seniority_levels=["entry", "mid"],
        work_modes=["remote"],
        locations=["Remote"],
        exclude_keywords=[],
    )
    job = JobPosting(
        source="linkedin",
        external_id="senior-1",
        title="Senior Software Engineer",
        company="Example",
        location="Remote",
        jd_text="Python engineer required. Minimum 6 years of professional experience.",
    )

    score, reasons = score_job(profile, job, None)

    assert score == 0
    assert any("Requires 6+ years; profile has 2" in reason for reason in reasons)


def test_partial_profile_update_preserves_absent_fields():
    profile = UserProfile(
        current_role="Engineer",
        current_company="Acme",
        seniority_levels=["entry", "mid"],
        work_modes=["remote"],
    )

    _apply_profile_data(profile, ProfileUpdate(current_role="Senior Engineer"))

    assert profile.current_role == "Senior Engineer"
    assert profile.current_company == "Acme"
    assert profile.work_modes == ["remote"]


def test_current_profile_returns_latest_active_profile(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'profiles.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(engine) as session:
        older = UserProfile(
            current_role="Older",
            updated_at=now - timedelta(days=1),
        )
        latest = UserProfile(current_role="Latest", updated_at=now)
        session.add_all([older, latest])
        session.commit()

        response = get_current_profile(session)

        assert response.id == latest.id
        assert response.current_role == "Latest"


def test_legacy_profile_strings_migrate_to_json_lists(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE user_profiles ("
                "id VARCHAR PRIMARY KEY, seniority_level VARCHAR, work_mode VARCHAR)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO user_profiles (id, seniority_level, work_mode) "
                "VALUES ('profile-1', 'entry', 'hybrid')"
            )
        )
    monkeypatch.setattr(database, "engine", engine)

    database._ensure_profile_preference_columns()

    columns = {column["name"] for column in inspect(engine).get_columns("user_profiles")}
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT seniority_levels, work_modes FROM user_profiles "
                "WHERE id = 'profile-1'"
            )
        ).mappings().one()
    assert {"seniority_levels", "work_modes"} <= columns
    assert json.loads(row["seniority_levels"]) == ["entry"]
    assert json.loads(row["work_modes"]) == ["hybrid"]
