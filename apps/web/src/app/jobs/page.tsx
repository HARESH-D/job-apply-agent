"use client";

import { useEffect, useState } from "react";
import { api, Job } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [minScore, setMinScore] = useState(50);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const profileId = localStorage.getItem(PROFILE_KEY);
    if (!profileId) {
      setMessage("Create a profile first.");
      return;
    }
    setLoading(true);
    try {
      const data = await api.listJobs(profileId, minScore);
      setJobs(data);
      setMessage(`${data.length} jobs found.`);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [minScore]);

  const tailor = async (matchId: string) => {
    try {
      const result = await api.tailorResume(matchId);
      setMessage(`Tailored: ${result.diff_summary}`);
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  return (
    <div>
      <h2>Matched Jobs</h2>
      <div className="card">
        <label>Minimum match score</label>
        <input type="number" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} />
        <button onClick={load} disabled={loading}>{loading ? "Loading..." : "Refresh"}</button>
      </div>
      {message && <p>{message}</p>}

      {jobs.map((job) => (
        <div key={job.id} className="card job-card">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <h3 style={{ margin: "0 0 0.5rem" }}>{job.title}</h3>
              <p style={{ margin: 0 }}>{job.company} · {job.location}</p>
            </div>
            <span className="score">{job.match_score?.toFixed(1)}%</span>
          </div>
          <ul className="reasons">
            {job.match_reasons?.map((r) => <li key={r}>{r}</li>)}
          </ul>
          <p style={{ fontSize: "0.9rem" }}>{job.jd_text?.slice(0, 300)}...</p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
            {job.url && <a href={job.url} target="_blank" rel="noreferrer">View job</a>}
            {job.match_id && job.match_status !== "tailored" && (
              <button onClick={() => tailor(job.match_id!)}>Tailor resume</button>
            )}
            {job.match_id && job.match_status === "tailored" && (
              <a href={api.downloadResumeUrl(job.match_id)} download>
                <button className="secondary">Download DOCX</button>
              </a>
            )}
          </div>
        </div>
      ))}
      {!loading && jobs.length === 0 && <p>No jobs yet. Run the local scraper worker.</p>}
    </div>
  );
}
