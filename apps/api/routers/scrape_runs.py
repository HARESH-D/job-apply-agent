import sys
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


@router.post("", response_model=ScrapeRunResponse, dependencies=[Depends(verify_worker_key)])
def create_scrape_run(data: ScrapeRunCreate, db: Session = Depends(get_db)):
    run = ScrapeRun(**data.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return ScrapeRunResponse(id=run.id, **data.model_dump())


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
            started_at=r.started_at,
            completed_at=r.completed_at,
            jobs_found=r.jobs_found,
            errors=r.errors,
            status=r.status,
        )
        for r in runs
    ]
