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

Uses SQLite by default (`jobagent.db`). Relative database and storage paths are
anchored to the repository root, so API and worker launches from different
directories share the same persisted profile. Optional Postgres + pgvector:

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

Profile work modes and seniority levels support multiple selections. Matching
hard-rejects jobs whose explicit years-of-experience requirement exceeds the
saved profile and rejects titles outside the selected levels.

Resume tailoring is local and deterministic by default. Gemini 2.5 Flash-Lite
is optional per request: enabling it sends the resume and job description to
Google under Google's data-use terms. Missing keys, quota errors, timeouts, and
invalid output fall back to local tailoring. All output is validated against
the verified base resume and rendered as a single-column ATS-safe DOCX.

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
