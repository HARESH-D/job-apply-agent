import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import jobs, matches, profiles, scrape_runs

app = FastAPI(title="Job Apply Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(scrape_runs.router)


DEFAULT_WORKER_KEY = "change-me-local-worker-key"


@app.on_event("startup")
def on_startup():
    if settings.worker_api_key == DEFAULT_WORKER_KEY:
        # Local Phase-1 convenience: warn loudly but do not hard-fail, so
        # first-time setup still works. Change WORKER_API_KEY before exposing
        # the API beyond localhost.
        print(
            "WARNING: WORKER_API_KEY is still the default placeholder. "
            "Set a unique value in .env before binding this API outside localhost."
        )
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
