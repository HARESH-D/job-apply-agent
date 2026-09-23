"use client";

import { useEffect, useState } from "react";
import { api, ScrapeRun } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

export default function ScraperPage() {
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"ok" | "err" | "">("");

  const load = () => {
    const profileId = localStorage.getItem(PROFILE_KEY);
    if (!profileId) {
      setMessage("Create a profile first.");
      setMessageTone("err");
      return;
    }
    api
      .listScrapeRuns(profileId)
      .then((data) => {
        setRuns(data);
        setMessage("");
        setMessageTone("");
      })
      .catch((e) => {
        setMessage(String(e));
        setMessageTone("err");
      });
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <h1 className="page-title">Scraper</h1>
      <p className="page-lede">
        Local worker on your PC — every 6 hours, jobs posted in the last 24h.
        Session cookies never leave this machine.
      </p>

      <section className="section">
        <div className="section-head">
          <h2>Setup</h2>
          <p>Run these once on your computer, then keep the daemon running.</p>
        </div>
        <pre className="code-panel">{`cd worker/scraper
pip install -r requirements.txt
playwright install chromium
python login.py          # one-time LinkedIn login
python daemon.py --once  # test run
python daemon.py         # start 6h scheduler`}</pre>
        <div className="actions">
          <button type="button" className="btn" onClick={load}>
            Refresh status
          </button>
        </div>
      </section>

      {message && (
        <p
          className={`toast ${messageTone === "ok" ? "toast-ok" : ""} ${messageTone === "err" ? "toast-err" : ""}`}
        >
          {message}
        </p>
      )}

      <section className="section">
        <div className="section-head">
          <h2>Recent runs</h2>
          <p>Latest scrape outcomes from the local worker.</p>
        </div>

        {runs.length === 0 && (
          <div className="empty-state">
            <strong>No scrape runs yet.</strong>
            <br />
            Run <code>python daemon.py --once</code> after login.
          </div>
        )}

        <div className="status-list">
          {runs.map((run) => {
            const ok = run.status === "completed";
            return (
              <div key={run.id} className="status-item">
                <p style={{ margin: 0 }}>
                  <span
                    className={`status-pill ${ok ? "status-ok" : "status-err"}`}
                  >
                    {run.status}
                  </span>
                  {" · "}
                  {run.jobs_found} jobs ·{" "}
                  {new Date(run.started_at).toLocaleString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                    second: "2-digit",
                    timeZoneName: "short",
                  })}
                </p>
                {run.errors && (
                  <p className="status-err hint" style={{ marginTop: "0.4rem" }}>
                    {run.errors}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
