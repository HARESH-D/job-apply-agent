import json
import shutil
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import ROOT, settings


def _migrate_legacy_sqlite_file(
    database_url: str, candidates: list[Path]
) -> bool:
    """Copy a pre-fix CWD-relative SQLite DB to its stable path once."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return False
    target = Path(database_url[len(prefix):])
    if target.exists():
        return False
    source = next(
        (candidate for candidate in candidates if candidate.exists()), None
    )
    if source is None:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


_migrate_legacy_sqlite_file(
    settings.database_url,
    [
        Path(__file__).resolve().parent / "jobagent.db",
        ROOT / "worker" / "scraper" / "jobagent.db",
    ],
)

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (  # noqa: F401
        JobMatch,
        JobPosting,
        ParsedResume,
        ScrapeRun,
        TailoredResume,
        UserProfile,
    )

    if settings.database_url.startswith("postgresql"):
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
    _ensure_profile_preference_columns()
    _ensure_job_metadata_columns()


def _ensure_profile_preference_columns() -> None:
    """Forward-only compatibility migration for existing local databases."""
    inspector = inspect(engine)
    if "user_profiles" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    missing = [
        name for name in ("seniority_levels", "work_modes") if name not in columns
    ]
    if not missing:
        return

    dialect = engine.dialect.name
    with engine.begin() as conn:
        for name in missing:
            conn.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {name} JSON"))

        rows = conn.execute(
            text("SELECT id, seniority_level, work_mode FROM user_profiles")
        ).mappings()
        for row in rows:
            values = {
                "id": row["id"],
                "seniority_levels": json.dumps(
                    [row["seniority_level"] or "mid"]
                ),
                "work_modes": json.dumps([row["work_mode"] or "any"]),
            }
            if dialect == "postgresql":
                conn.execute(
                    text(
                        "UPDATE user_profiles "
                        "SET seniority_levels = CAST(:seniority_levels AS JSON), "
                        "work_modes = CAST(:work_modes AS JSON) WHERE id = :id"
                    ),
                    values,
                )
            else:
                conn.execute(
                    text(
                        "UPDATE user_profiles SET seniority_levels = :seniority_levels, "
                        "work_modes = :work_modes WHERE id = :id"
                    ),
                    values,
                )


def _ensure_job_metadata_columns() -> None:
    inspector = inspect(engine)
    if "job_postings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("job_postings")}
    dialect = engine.dialect.name
    boolean_true = "TRUE" if dialect == "postgresql" else "1"
    boolean_false = "FALSE" if dialect == "postgresql" else "0"
    definitions = {
        "workplace_type": "VARCHAR(16) DEFAULT 'unknown'",
        "is_accepting_applications": f"BOOLEAN DEFAULT {boolean_true}",
        "is_promoted": f"BOOLEAN DEFAULT {boolean_false}",
    }
    missing = [name for name in definitions if name not in columns]
    if not missing:
        return
    with engine.begin() as conn:
        for name in missing:
            conn.execute(
                text(
                    f"ALTER TABLE job_postings ADD COLUMN {name} "
                    f"{definitions[name]}"
                )
            )
        conn.execute(
            text(
                "UPDATE job_postings SET workplace_type = 'unknown' "
                "WHERE workplace_type IS NULL"
            )
        )
        conn.execute(
            text(
                f"UPDATE job_postings SET is_accepting_applications = {boolean_true} "
                "WHERE is_accepting_applications IS NULL"
            )
        )
        conn.execute(
            text(
                f"UPDATE job_postings SET is_promoted = {boolean_false} "
                "WHERE is_promoted IS NULL"
            )
        )
