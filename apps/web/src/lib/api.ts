const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export interface Profile {
  id: string;
  target_roles: string[];
  skills_must_have: string[];
  skills_nice_to_have: string[];
  experience_years: number;
  seniority_levels: string[];
  seniority_level?: string;
  locations: string[];
  work_modes: string[];
  work_mode?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency: string;
  current_role: string;
  current_company: string;
  industry: string;
  exclude_keywords: string[];
  max_jobs_per_run: number;
  match_threshold: number;
  has_resume: boolean;
  contact: Record<string, string>;
  education: Array<{ institution: string; degree: string; year: string }>;
  certifications: string[];
}

export interface Job {
  id: string;
  title: string;
  company: string;
  company_tier: string;
  company_tier_label: string;
  location: string;
  workplace_type: string;
  is_accepting_applications: boolean;
  is_promoted: boolean;
  jd_text: string;
  url: string;
  match_score?: number;
  match_reasons: string[];
  match_id?: string;
  match_status?: string;
  posted_at?: string;
}

export interface ScrapeRun {
  id: string;
  started_at: string;
  completed_at?: string;
  jobs_found: number;
  errors: string;
  status: string;
}

export const api = {
  createProfile: (data: Partial<Profile>) =>
    request<Profile>("/profiles", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),

  updateProfile: (id: string, data: Partial<Profile>) =>
    request<Profile>(`/profiles/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),

  getProfile: (id: string) => request<Profile>(`/profiles/${id}`),
  getCurrentProfile: () => request<Profile>("/profiles/current"),

  uploadResume: async (id: string, file: File, useGemini = false) => {
    const form = new FormData();
    form.append("file", file);
    form.append("use_gemini", String(useGemini));
    form.append("consent_to_google_processing", String(useGemini));
    const res = await fetch(`${API_BASE}/profiles/${id}/resume`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getParsedResume: (id: string) => request<Record<string, unknown>>(`/profiles/${id}/resume/parsed`),

  listJobs: (profileId: string, minScore = 35) =>
    request<Job[]>(`/jobs?profile_id=${profileId}&min_score=${minScore}`),

  listScrapeRuns: (profileId: string) =>
    request<ScrapeRun[]>(`/scrape-runs?profile_id=${profileId}`),

  tailorResume: (matchId: string, useGemini = false) =>
    request<{ match_id: string; diff_summary: string; validation_report: string[] }>(
      `/matches/${matchId}/tailor`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          use_gemini: useGemini,
          consent_to_google_processing: useGemini,
        }),
      },
    ),

  downloadResumeUrl: (matchId: string) => `${API_BASE}/matches/${matchId}/resume`,
};
