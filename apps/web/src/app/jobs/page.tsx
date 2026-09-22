"use client";

import { useEffect, useState } from "react";
import { api, Job } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [minScore, setMinScore] = useState(50);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"ok" | "err" | "">("");
  const [loading, setLoading] = useState(false);
  const [useGemini, setUseGemini] = useState(false);
  const [tailoringId, setTailoringId] = useState<string | null>(null);

  const load = async () => {
    const profileId = localStorage.getItem(PROFILE_KEY);
    if (!profileId) {
      setMessage("Create a profile first.");
      setMessageTone("err");
      return;
    }
    setLoading(true);
    try {
      const data = await api.listJobs(profileId, minScore);
      setJobs(data);
      setMessage(`${data.length} jobs above ${minScore}%`);
      setMessageTone("ok");
    } catch (e) {
      setMessage(String(e));
      setMessageTone("err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minScore]);

  const tailor = async (matchId: string) => {
    setTailoringId(matchId);
    try {
      const result = await api.tailorResume(matchId, useGemini);
      setMessage(`Tailored: ${result.diff_summary}`);
      setMessageTone("ok");
      load();
    } catch (e) {
      setMessage(String(e));
      setMessageTone("err");
    } finally {
      setTailoringId(null);
    }
  };

  return (
    <div>
      <h1 className="page-title">Matched jobs</h1>
      <p className="page-lede">
        Ranked against your profile. Tailor an ATS resume for any listing above
        your threshold.
      </p>

      <div className="tool-strip">
        <div className="field">
          <label>Minimum score</label>
          <input
            type="number"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
          />
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={load}
          disabled={loading}
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      <section className="privacy-consent">
        <label>
          <input
            type="checkbox"
            checked={useGemini}
            onChange={(event) => setUseGemini(event.target.checked)}
          />
          <span>Use Gemini 2.5 Flash-Lite for this tailoring request</span>
        </label>
        <p>
          When enabled, your resume and the job description are sent to Google.
          Google&apos;s free-tier data-use terms may allow service improvement.
          Leave this unchecked to use the private local tailoring pipeline.
        </p>
      </section>

      {message && (
        <p
          role={messageTone === "err" ? "alert" : "status"}
          aria-live="polite"
          className={`toast ${messageTone === "ok" ? "toast-ok" : ""} ${messageTone === "err" ? "toast-err" : ""}`}
        >
          {message}
        </p>
      )}

      {!loading && jobs.length === 0 && (
        <div className="empty-state">
          <strong>No matches yet.</strong>
          <br />
          Save a profile, run the local scraper, then refresh.
        </div>
      )}

      <div className="job-list">
        {jobs.map((job, index) => (
          <article
            key={job.id}
            className="job-row"
            style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}
          >
            <div className="job-row-top">
              <div>
                <h3>{job.title}</h3>
                <p className="job-meta">
                  {job.company} · {job.location}
                </p>
              </div>
              {job.match_score != null && (
                <span className="score-badge">
                  {job.match_score.toFixed(0)}%
                </span>
              )}
            </div>
            {job.match_reasons && job.match_reasons.length > 0 && (
              <ul className="reasons">
                {job.match_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
            {job.jd_text && (
              <p className="job-excerpt">{job.jd_text.slice(0, 280)}…</p>
            )}
            <div className="actions">
              {job.url && (
                <a
                  className="btn btn-ghost"
                  href={job.url}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  View job
                </a>
              )}
              {job.match_id && (
                <button
                  type="button"
                  className="btn"
                  onClick={() => tailor(job.match_id!)}
                  disabled={tailoringId === job.match_id}
                >
                  {tailoringId === job.match_id
                    ? "Tailoring…"
                    : job.match_status === "tailored"
                      ? "Tailor new version"
                      : "Tailor resume"}
                </button>
              )}
              {job.match_id && job.match_status === "tailored" && (
                <a
                  className="btn btn-secondary"
                  href={api.downloadResumeUrl(job.match_id)}
                  download
                >
                  Download DOCX
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
