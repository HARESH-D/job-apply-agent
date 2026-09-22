"use client";

import { useEffect, useState } from "react";
import { api, Profile } from "@/lib/api";

const PROFILE_KEY = "job_apply_profile_id";

function parseList(value: string): string[] {
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

type ParsedResumeView = {
  name?: string;
  summary?: string;
  skills_must_have?: string[];
  skills_nice_to_have?: string[];
  experience?: Array<{
    company?: string;
    role?: string;
    bullets?: string[];
  }>;
  education?: Array<{ institution?: string; degree?: string; year?: string }>;
  contact?: { email?: string; phone?: string };
};

function ResumePreview({ data }: { data: Record<string, unknown> }) {
  const r = data as ParsedResumeView;
  const skills = [
    ...(r.skills_must_have || []),
    ...(r.skills_nice_to_have || []),
  ];

  return (
    <div className="resume-preview">
      {(r.name || r.contact?.email) && (
        <div className="resume-block">
          <h4>{r.name || "Candidate"}</h4>
          <p>
            {[r.contact?.email, r.contact?.phone].filter(Boolean).join(" · ") ||
              "—"}
          </p>
        </div>
      )}
      {r.summary && (
        <div className="resume-block">
          <h4>Summary</h4>
          <p>{r.summary}</p>
        </div>
      )}
      {skills.length > 0 && (
        <div className="resume-block">
          <h4>Skills</h4>
          <div className="resume-skills">
            {skills.slice(0, 24).map((s) => (
              <span key={s}>{s}</span>
            ))}
          </div>
        </div>
      )}
      {r.experience && r.experience.length > 0 && (
        <div className="resume-block">
          <h4>Experience</h4>
          <ul>
            {r.experience.slice(0, 5).map((exp, i) => (
              <li key={`${exp.role}-${i}`}>
                <strong>{exp.role || "Role"}</strong>
                {exp.company ? ` · ${exp.company}` : ""}
                {exp.bullets?.[0] ? ` — ${exp.bullets[0].slice(0, 120)}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.education && r.education.length > 0 && (
        <div className="resume-block">
          <h4>Education</h4>
          <ul>
            {r.education.slice(0, 4).map((edu, i) => (
              <li key={`${edu.institution}-${i}`}>
                {[edu.institution, edu.degree, edu.year]
                  .filter(Boolean)
                  .join(" · ")}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const [profileId, setProfileId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"ok" | "err" | "">("");
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
      api
        .getProfile(id)
        .then((p) => {
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
        })
        .catch(() => localStorage.removeItem(PROFILE_KEY));
    }
  }, []);

  const set =
    (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm({ ...form, [key]: e.target.value });

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
    contact: {
      email: form.email,
      phone: form.phone,
      linkedin: form.linkedin,
      github: form.github,
    },
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
      setMessageTone("ok");
    } catch (e) {
      setMessage(String(e));
      setMessageTone("err");
    }
  };

  const onResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profileId) return;
    try {
      const result = await api.uploadResume(profileId, file);
      setParsed(result);
      setMessage("Resume parsed.");
      setMessageTone("ok");
    } catch (err) {
      setMessage(String(err));
      setMessageTone("err");
    }
  };

  return (
    <div>
      <h1 className="page-title">Your profile</h1>
      <p className="page-lede">
        Targets, skills, and preferences that drive matching and resume
        tailoring.
      </p>

      {message && (
        <p
          className={`toast ${messageTone === "ok" ? "toast-ok" : ""} ${messageTone === "err" ? "toast-err" : ""}`}
        >
          {message}
        </p>
      )}

      <section className="section">
        <div className="section-head">
          <h2>Targets</h2>
          <p>Roles and places you want to apply to.</p>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Target roles</label>
            <input
              value={form.target_roles}
              onChange={set("target_roles")}
              placeholder="Software Engineer, Backend Developer"
            />
          </div>
          <div className="field">
            <label>Locations</label>
            <input
              value={form.locations}
              onChange={set("locations")}
              placeholder="Bangalore, Remote"
            />
          </div>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Work mode</label>
            <select value={form.work_mode} onChange={set("work_mode")}>
              <option value="any">Any</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </select>
          </div>
          <div className="field">
            <label>Seniority</label>
            <select value={form.seniority_level} onChange={set("seniority_level")}>
              <option value="entry">Entry</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </select>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Skills</h2>
          <p>Comma-separated. Must-haves weigh more in scoring.</p>
        </div>
        <div className="field">
          <label>Must-have skills</label>
          <input
            value={form.skills_must_have}
            onChange={set("skills_must_have")}
          />
        </div>
        <div className="field">
          <label>Nice-to-have skills</label>
          <input
            value={form.skills_nice_to_have}
            onChange={set("skills_nice_to_have")}
          />
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Experience (years)</label>
            <input
              value={form.experience_years}
              onChange={set("experience_years")}
            />
          </div>
          <div className="field">
            <label>Industry</label>
            <input value={form.industry} onChange={set("industry")} />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Compensation</h2>
          <p>Used as a hard filter when jobs list salary.</p>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Salary min</label>
            <input value={form.salary_min} onChange={set("salary_min")} />
          </div>
          <div className="field">
            <label>Salary max</label>
            <input value={form.salary_max} onChange={set("salary_max")} />
          </div>
        </div>
        <div className="field">
          <label>Currency</label>
          <input value={form.salary_currency} onChange={set("salary_currency")} />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Preferences</h2>
          <p>Current role context and matching knobs.</p>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Current role</label>
            <input value={form.current_role} onChange={set("current_role")} />
          </div>
          <div className="field">
            <label>Current company</label>
            <input
              value={form.current_company}
              onChange={set("current_company")}
            />
          </div>
        </div>
        <div className="field">
          <label>Exclude keywords</label>
          <input
            value={form.exclude_keywords}
            onChange={set("exclude_keywords")}
          />
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Match threshold (%)</label>
            <input
              value={form.match_threshold}
              onChange={set("match_threshold")}
            />
          </div>
          <div className="field">
            <label>Max jobs per scrape</label>
            <input
              value={form.max_jobs_per_run}
              onChange={set("max_jobs_per_run")}
            />
          </div>
        </div>
        <div className="actions">
          <button type="button" className="btn" onClick={save}>
            Save profile
          </button>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Resume</h2>
          <p>Upload a PDF or DOCX. Parsing feeds skills and experience into matching.</p>
        </div>
        <input
          className="file-input"
          type="file"
          accept=".pdf,.docx"
          onChange={onResumeUpload}
          disabled={!profileId}
        />
        {!profileId && (
          <p className="hint">Save your profile first, then upload a resume.</p>
        )}
        {parsed && (
          <>
            <h3
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1rem",
                marginTop: "1.5rem",
                marginBottom: 0,
              }}
            >
              Parsed preview
            </h3>
            <ResumePreview data={parsed} />
          </>
        )}
      </section>
    </div>
  );
}
