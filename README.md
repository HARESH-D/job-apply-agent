# Job Apply Agent (Local)

Personal job-application agent — profile → scrape → match → ATS resume tailor.

## Important — read before using

- **Localhost only.** The API has no user auth. Do not expose ports 8000/3000 to the internet.
- **LinkedIn scraping is at your own risk.** The worker uses your logged-in browser session. That may violate LinkedIn’s Terms of Service and can get your account restricted. Keep `storage_state.json` on your machine — never commit or share it.
- **No auto-apply.** Phase 1 only scrapes, scores, and generates tailored DOCX resumes for you to review.
- Change `WORKER_API_KEY` in `.env` from the placeholder before any non-local use.

## Quick start

### 1. API

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy ..\..\.env.example ..\..\.env
uvicorn main:app --reload --port 8000
```

Uses SQLite by default (`jobagent.db`). Optional Postgres + pgvector:

```powershell
cd infra
docker compose up -d
```

Set in `.env`: `DATABASE_URL=postgresql://jobagent:jobagent@localhost:5433/jobagent`

### 2. Web UI

```powershell
cd apps\web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 3. Local scraper (your PC)

```powershell
cd worker\scraper
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python login.py
python daemon.py --once
```

If scrape status looks wrong, run `python diagnose.py` first.

## Docs

- **Feature spec:** [docs/FEATURES.md](docs/FEATURES.md)

## Architecture

- **Local:** Next.js UI + FastAPI + SQLite/Postgres
- **Your PC:** Playwright LinkedIn scraper (6h cron, residential IP, no static IP needed)
