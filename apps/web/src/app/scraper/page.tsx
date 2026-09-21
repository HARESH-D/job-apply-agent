"use client";

import { useEffect, useState } from "react";
import { api, ScrapeRun } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

export default function ScraperPage() {
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [message, setMessage] = useState("");

  const load = () => {
    const profileId = localStorage.getItem(PROFILE_KEY);
    if (!profileId) {
      setMessage("Create a profile first.");
      return;
    }
    api.listScrapeRuns(profileId).then(setRuns).catch((e) => setMessage(String(e)));
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>Scraper Status</h2>
      <div className="card">
        <p>Local worker runs every <strong>6 hours</strong> (4×/day). Fetches jobs posted in last 24h.</p>
        <h4>Setup (run on your PC)</h4>
        <pre>{`cd worker/scraper
pip install -r requirements.txt
playwright install chromium
python login.py          # one-time LinkedIn login
python daemon.py --once  # test run
python daemon.py         # start 6h scheduler`}</pre>
        <button onClick={load}>Refresh status</button>
      </div>
      {message && <p>{message}</p>}
      {runs.map((run) => (
        <div key={run.id} className="card">
          <p>
            <span className={run.status === "completed" ? "status-ok" : "status-err"}>
              {run.status}
            </span>
            {" · "}{run.jobs_found} jobs · {new Date(run.started_at).toLocaleString()}
          </p>
          {run.errors && <p className="status-err">{run.errors}</p>}
        </div>
      ))}
      {runs.length === 0 && <p>No scrape runs yet.</p>}
    </div>
  );
}
