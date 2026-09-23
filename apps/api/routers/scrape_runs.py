import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import get_db
from deps import verify_worker_key
from models import ScrapeRun
from packages.shared.schemas import ScrapeRunCreate, ScrapeRunResponse

router = APIRouter(prefix="/scrape-runs", tags=["scrape-runs"])


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.post("", response_model=ScrapeRunResponse, dependencies=[Depends(verify_worker_key)])
def create_scrape_run(data: ScrapeRunCreate, db: Session = Depends(get_db)):
    run = ScrapeRun(**data.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    response = data.model_dump()
    response["started_at"] = _as_utc(response["started_at"])
    response["completed_at"] = _as_utc(response["completed_at"])
    return ScrapeRunResponse(id=run.id, **response)


@router.get("", response_model=list[ScrapeRunResponse])
def list_scrape_runs(profile_id: UUID = Query(...), db: Session = Depends(get_db)):
    runs = (
        db.query(ScrapeRun)
        .filter(ScrapeRun.profile_id == profile_id)
        .order_by(ScrapeRun.started_at.desc())
        .limit(20)
        .all()
    )
    return [
        ScrapeRunResponse(
            id=r.id,
            profile_id=r.profile_id,
            started_at=_as_utc(r.started_at),
            completed_at=_as_utc(r.completed_at),
            jobs_found=r.jobs_found,
            errors=r.errors,
            status=r.status,
        )
        for r in runs
    ]
