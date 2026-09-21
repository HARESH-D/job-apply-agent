"use client";

import { useEffect, useState } from "react";
import { api, Profile } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

function parseList(value: string): string[] {
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

export default function ProfilePage() {
  const [profileId, setProfileId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState({
    target_roles: "Software Engineer, Backend Developer",
    skills_must_have: "Python, FastAPI, PostgreSQL, React",
    skills_nice_to_have: "AWS, Docker, LangGraph",
    experience_years: "2",
    seniority_level: "mid",
    locations: "Bangalore, Remote",
    work_mode: "any",
    salary_min: "800000",
    salary_max: "1500000",
    salary_currency: "INR",
    current_role: "Software Engineer",
    current_company: "",
    industry: "Technology",
    exclude_keywords: "sales, clearance",
    max_jobs_per_run: "50",
    match_threshold: "50",
    email: "",
    phone: "",
    linkedin: "",
    github: "",
  });

  useEffect(() => {
    const id = localStorage.getItem(PROFILE_KEY);
    if (id) {
      setProfileId(id);
      api.getProfile(id).then((p) => {
        setForm({
          target_roles: p.target_roles.join(", "),
          skills_must_have: p.skills_must_have.join(", "),
          skills_nice_to_have: p.skills_nice_to_have.join(", "),
          experience_years: String(p.experience_years),
          seniority_level: p.seniority_level,
          locations: p.locations.join(", "),
          work_mode: p.work_mode,
          salary_min: String(p.salary_min ?? ""),
          salary_max: String(p.salary_max ?? ""),
          salary_currency: p.salary_currency,
          current_role: p.current_role,
          current_company: p.current_company,
          industry: p.industry,
          exclude_keywords: p.exclude_keywords.join(", "),
          max_jobs_per_run: String(p.max_jobs_per_run),
          match_threshold: String(p.match_threshold),
          email: p.contact?.email || "",
          phone: p.contact?.phone || "",
          linkedin: p.contact?.linkedin || "",
          github: p.contact?.github || "",
        });
        if (p.has_resume) api.getParsedResume(id).then(setParsed).catch(() => null);
      }).catch(() => localStorage.removeItem(PROFILE_KEY));
    }
  }, []);

  const buildPayload = (): Partial<Profile> => ({
    target_roles: parseList(form.target_roles),
    skills_must_have: parseList(form.skills_must_have),
    skills_nice_to_have: parseList(form.skills_nice_to_have),
    experience_years: parseFloat(form.experience_years) || 0,
    seniority_level: form.seniority_level,
    locations: parseList(form.locations),
    work_mode: form.work_mode,
    salary_min: form.salary_min ? parseFloat(form.salary_min) : undefined,
    salary_max: form.salary_max ? parseFloat(form.salary_max) : undefined,
    salary_currency: form.salary_currency,
    current_role: form.current_role,
    current_company: form.current_company,
    industry: form.industry,
    exclude_keywords: parseList(form.exclude_keywords),
    max_jobs_per_run: parseInt(form.max_jobs_per_run) || 50,
    match_threshold: parseFloat(form.match_threshold) || 50,
    contact: { email: form.email, phone: form.phone, linkedin: form.linkedin, github: form.github },
  });

  const save = async () => {
    try {
      const payload = buildPayload();
      const p = profileId
        ? await api.updateProfile(profileId, payload)
        : await api.createProfile(payload);
      localStorage.setItem(PROFILE_KEY, p.id);
      setProfileId(p.id);
      setMessage("Profile saved.");
    } catch (e) {
      setMessage(String(e));
    }
  };

  const onResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profileId) return;
    try {
      const result = await api.uploadResume(profileId, file);
      setParsed(result);
      setMessage("Resume parsed.");
    } catch (err) {
      setMessage(String(err));
    }
  };

  return (
    <div>
      <h2>Your Profile</h2>
      {message && <p>{message}</p>}

      <div className="card">
        <div className="grid-2">
          <div>
            <label>Target roles (comma-separated)</label>
            <input value={form.target_roles} onChange={(e) => setForm({ ...form, target_roles: e.target.value })} />
          </div>
          <div>
            <label>Locations</label>
            <input value={form.locations} onChange={(e) => setForm({ ...form, locations: e.target.value })} />
          </div>
        </div>
        <label>Must-have skills</label>
        <input value={form.skills_must_have} onChange={(e) => setForm({ ...form, skills_must_have: e.target.value })} />
        <label>Nice-to-have skills</label>
        <input value={form.skills_nice_to_have} onChange={(e) => setForm({ ...form, skills_nice_to_have: e.target.value })} />
        <div className="grid-2">
          <div>
            <label>Experience (years)</label>
            <input value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: e.target.value })} />
          </div>
          <div>
            <label>Seniority</label>
            <select value={form.seniority_level} onChange={(e) => setForm({ ...form, seniority_level: e.target.value })}>
              <option value="entry">Entry</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </select>
          </div>
        </div>
        <div className="grid-2">
          <div>
            <label>Salary min</label>
            <input value={form.salary_min} onChange={(e) => setForm({ ...form, salary_min: e.target.value })} />
          </div>
          <div>
            <label>Salary max</label>
            <input value={form.salary_max} onChange={(e) => setForm({ ...form, salary_max: e.target.value })} />
          </div>
        </div>
        <label>Current role / company / industry</label>
        <div className="grid-2">
          <input placeholder="Role" value={form.current_role} onChange={(e) => setForm({ ...form, current_role: e.target.value })} />
          <input placeholder="Company" value={form.current_company} onChange={(e) => setForm({ ...form, current_company: e.target.value })} />
        </div>
        <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
        <label>Exclude keywords</label>
        <input value={form.exclude_keywords} onChange={(e) => setForm({ ...form, exclude_keywords: e.target.value })} />
        <div className="grid-2">
          <div>
            <label>Match threshold (%)</label>
            <input value={form.match_threshold} onChange={(e) => setForm({ ...form, match_threshold: e.target.value })} />
          </div>
          <div>
            <label>Max jobs per scrape run</label>
            <input value={form.max_jobs_per_run} onChange={(e) => setForm({ ...form, max_jobs_per_run: e.target.value })} />
          </div>
        </div>
        <button onClick={save}>Save Profile</button>
      </div>

      <div className="card">
        <h3>Resume Upload</h3>
        <input type="file" accept=".pdf,.docx" onChange={onResumeUpload} disabled={!profileId} />
        {!profileId && <p>Save profile first.</p>}
        {parsed && (
          <>
            <h4>Parsed resume preview</h4>
            <pre>{JSON.stringify(parsed, null, 2)}</pre>
          </>
        )}
      </div>
    </div>
  );
}
