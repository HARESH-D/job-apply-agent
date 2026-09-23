"use client";

import { useEffect, useState } from "react";
import { api, Profile } from "@/lib/api";
import { MultiSelect } from "@/components/MultiSelect";

const PROFILE_KEY = "job_apply_profile_id";
const SENIORITY_OPTIONS = [
  { value: "entry", label: "Entry" },
  { value: "mid", label: "Mid" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
];
const WORK_MODE_OPTIONS = [
  { value: "any", label: "Any work mode" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];

function parseList(value: string): string[] {
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

function parseEducation(value: string) {
  return value
    .split("\n")
    .map((line) => line.split("|").map((piece) => piece.trim()))
    .filter((parts) => parts.some(Boolean))
    .map(([degree = "", institution = "", year = ""]) => ({
      degree,
      institution,
      year,
    }));
}

type ParsedResumeView = {
  name?: string;
  summary?: string;
  skills_must_have?: string[];
  skills_nice_to_have?: string[];
  experience?: Array<{
    company?: string;
    role?: string;
    start_date?: string;
    end_date?: string;
    bullets?: string[];
  }>;
  projects?: Array<{
    name?: string;
    technologies?: string[];
    bullets?: string[];
  }>;
  education?: Array<{ institution?: string; degree?: string; year?: string }>;
  certifications?: string[];
  achievements?: string[];
  extraction_warnings?: string[];
  contact?: {
    email?: string;
    phone?: string;
    linkedin?: string;
    github?: string;
    portfolio?: string;
  };
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
            {[
              r.contact?.email,
              r.contact?.phone,
              r.contact?.linkedin,
              r.contact?.github,
              r.contact?.portfolio,
            ]
              .filter(Boolean)
              .join(" · ") || "—"}
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
                {exp.start_date || exp.end_date
                  ? ` · ${[exp.start_date, exp.end_date].filter(Boolean).join(" – ")}`
                  : ""}
                {exp.bullets?.[0] ? ` — ${exp.bullets[0].slice(0, 120)}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.projects && r.projects.length > 0 && (
        <div className="resume-block">
          <h4>Projects</h4>
          <ul>
            {r.projects.map((project, index) => (
              <li key={`${project.name}-${index}`}>
                <strong>{project.name || "Project"}</strong>
                {project.technologies?.length
                  ? ` · ${project.technologies.join(", ")}`
                  : ""}
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
      {r.certifications && r.certifications.length > 0 && (
        <div className="resume-block">
          <h4>Certifications</h4>
          <p>{r.certifications.join(" · ")}</p>
        </div>
      )}
      {r.achievements && r.achievements.length > 0 && (
        <div className="resume-block">
          <h4>Achievements</h4>
          <ul>{r.achievements.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}
      {r.extraction_warnings && r.extraction_warnings.length > 0 && (
        <div className="resume-warning" role="alert">
          <strong>Review extraction</strong>
          <ul>
            {r.extraction_warnings.map((warning) => (
              <li key={warning}>{warning}</li>
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
  const [messageContext, setMessageContext] = useState<"load" | "save" | "upload">("load");
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [useGeminiExtraction, setUseGeminiExtraction] = useState(false);
  const [form, setForm] = useState({
    target_roles: "Software Engineer, Backend Developer",
    skills_must_have: "Python, FastAPI, PostgreSQL, React",
    skills_nice_to_have: "AWS, Docker, LangGraph",
    experience_years: "2",
    seniority_levels: ["entry", "mid"],
    locations: "Bangalore, Remote",
    work_modes: ["remote", "hybrid"],
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
    portfolio: "",
    education: "",
    certifications: "",
  });

  useEffect(() => {
    const hydrate = (p: Profile) => {
      setProfileId(p.id);
      localStorage.setItem(PROFILE_KEY, p.id);
      setForm({
        target_roles: p.target_roles.join(", "),
        skills_must_have: p.skills_must_have.join(", "),
        skills_nice_to_have: p.skills_nice_to_have.join(", "),
        experience_years: String(p.experience_years),
        seniority_levels:
          p.seniority_levels?.length
            ? p.seniority_levels
            : [p.seniority_level || "mid"],
        locations: p.locations.join(", "),
        work_modes:
          p.work_modes?.length ? p.work_modes : [p.work_mode || "remote"],
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
        portfolio: p.contact?.portfolio || "",
        education: (p.education || [])
          .map((entry) =>
            [entry.degree, entry.institution, entry.year].filter(Boolean).join(" | "),
          )
          .join("\n"),
        certifications: (p.certifications || []).join(", "),
      });
      if (p.has_resume) api.getParsedResume(p.id).then(setParsed).catch(() => null);
    };

    const load = async () => {
      const cachedId = localStorage.getItem(PROFILE_KEY);
      try {
        const profile = await api
          .getCurrentProfile()
          .catch(() =>
            cachedId ? api.getProfile(cachedId) : Promise.reject(),
          );
        hydrate(profile);
      } catch {
        localStorage.removeItem(PROFILE_KEY);
        setMessageContext("load");
        setMessage(
          cachedId
            ? "Your cached profile could not be recovered. Review the fields before saving."
            : "No saved profile found. Complete the fields to create one.",
        );
        setMessageTone(cachedId ? "err" : "");
      } finally {
        setLoadingProfile(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!message || messageTone !== "ok") return;
    const timer = window.setTimeout(() => setMessage(""), 3500);
    return () => window.clearTimeout(timer);
  }, [message, messageTone]);

  const set =
    (key: Exclude<keyof typeof form, "seniority_levels" | "work_modes">) =>
    (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >,
    ) =>
      setForm({ ...form, [key]: e.target.value });

  const buildPayload = (): Partial<Profile> => ({
    target_roles: parseList(form.target_roles),
    skills_must_have: parseList(form.skills_must_have),
    skills_nice_to_have: parseList(form.skills_nice_to_have),
    experience_years: parseFloat(form.experience_years) || 0,
    seniority_levels: form.seniority_levels,
    locations: parseList(form.locations),
    work_modes: form.work_modes,
    salary_min: form.salary_min ? parseFloat(form.salary_min) : undefined,
    salary_max: form.salary_max ? parseFloat(form.salary_max) : undefined,
    salary_currency: form.salary_currency,
    current_role: form.current_role,
    current_company: form.current_company,
    industry: form.industry,
    exclude_keywords: parseList(form.exclude_keywords),
    max_jobs_per_run: parseInt(form.max_jobs_per_run) || 50,
    match_threshold: parseFloat(form.match_threshold) || 50,
    education: parseEducation(form.education),
    certifications: parseList(form.certifications),
    contact: {
      email: form.email,
      phone: form.phone,
      linkedin: form.linkedin,
      github: form.github,
      portfolio: form.portfolio,
    },
  });

  const save = async () => {
    setSaving(true);
    setMessageContext("save");
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
    } finally {
      setSaving(false);
    }
  };

  const onResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profileId) return;
    setUploading(true);
    setMessageContext("upload");
    try {
      const result = await api.uploadResume(
        profileId,
        file,
        useGeminiExtraction,
      );
      setParsed(result);
      setMessage("Resume parsed.");
      setMessageTone("ok");
    } catch (err) {
      setMessage(String(err));
      setMessageTone("err");
    } finally {
      setUploading(false);
    }
  };

  if (loadingProfile) {
    return (
      <div className="empty-state" role="status">
        <strong>Loading your saved profile…</strong>
      </div>
    );
  }

  return (
    <div>
      <h1 className="page-title">Your profile</h1>
      <p className="page-lede">
        Targets, skills, and preferences that drive matching and resume
        tailoring.
      </p>

      {message && messageContext !== "save" && (
        <p
          role={messageTone === "err" ? "alert" : "status"}
          aria-live="polite"
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
            <label>Work modes</label>
            <MultiSelect
              label="work modes"
              options={WORK_MODE_OPTIONS}
              values={form.work_modes}
              onChange={(work_modes) => setForm({ ...form, work_modes })}
            />
          </div>
          <div className="field">
            <label>Seniority levels</label>
            <MultiSelect
              label="seniority levels"
              options={SENIORITY_OPTIONS}
              values={form.seniority_levels}
              onChange={(seniority_levels) =>
                setForm({ ...form, seniority_levels })
              }
            />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Resume facts</h2>
          <p>Verified details included in every tailored resume.</p>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={set("email")} />
          </div>
          <div className="field">
            <label>Phone</label>
            <input value={form.phone} onChange={set("phone")} />
          </div>
          <div className="field">
            <label>LinkedIn</label>
            <input value={form.linkedin} onChange={set("linkedin")} />
          </div>
          <div className="field">
            <label>GitHub</label>
            <input value={form.github} onChange={set("github")} />
          </div>
        </div>
        <div className="field">
          <label>Portfolio</label>
          <input value={form.portfolio} onChange={set("portfolio")} />
        </div>
        <div className="field">
          <label>Education</label>
          <textarea
            rows={3}
            value={form.education}
            onChange={set("education")}
            placeholder="BSc Computer Science | Example University | 2022"
          />
          <span className="hint">One entry per line: degree | institution | year</span>
        </div>
        <div className="field">
          <label>Certifications</label>
          <input
            value={form.certifications}
            onChange={set("certifications")}
            placeholder="AWS Developer, CKA"
          />
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
          <button
            type="button"
            className="btn"
            onClick={save}
            disabled={saving}
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
          {message && messageContext === "save" && (
            <span
              className={`action-status ${messageTone === "ok" ? "action-status-ok" : "action-status-err"}`}
              role={messageTone === "err" ? "alert" : "status"}
              aria-live="polite"
            >
              {message}
            </span>
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Resume</h2>
          <p>Upload a PDF or DOCX. Parsing feeds skills and experience into matching.</p>
        </div>
        <div className="privacy-consent">
          <label>
            <input
              type="checkbox"
              checked={useGeminiExtraction}
              onChange={(event) =>
                setUseGeminiExtraction(event.target.checked)
              }
            />
            <span>Use Gemini to repair difficult resume extraction</span>
          </label>
          <p>
            Optional. When enabled, the resume text is sent to Google under
            Google&apos;s data-use terms. Local extraction remains the fallback.
          </p>
        </div>
        <input
          className="file-input"
          type="file"
          accept=".pdf,.docx"
          onChange={onResumeUpload}
          disabled={!profileId || uploading}
        />
        {uploading && <p className="hint">Parsing resume…</p>}
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
