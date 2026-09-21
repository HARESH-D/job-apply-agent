"""Score the real scraped jobs against a known-aligned profile.

Sanity check that the threshold is reachable with representative data — run it
after changing the scoring weights.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import SessionLocal
from models import JobPosting, UserProfile
from packages.shared.schemas import ExperienceEntry, ParsedResume
from services.match_engine import score_job

REFERENCE_PROFILE = UserProfile(
    target_roles=["Full Stack Developer", "Software Engineer", "Backend Developer"],
    skills_must_have=["Python", "React", "Node.js", "JavaScript", "AWS", "Docker", "SQL", "REST API"],
    skills_nice_to_have=["TypeScript", "MongoDB", "CI/CD", "Kubernetes", "Microservices"],
    experience_years=3,
    seniority_level="mid",
    locations=["Bangalore", "Remote"],
    work_mode="any",
    exclude_keywords=["clearance"],
    current_role="Full Stack Developer",
    current_company="TechCo",
    industry="Technology",
    match_threshold=50.0,
    max_jobs_per_run=50,
)

REFERENCE_RESUME = ParsedResume(
    name="Reference Dev",
    summary="Full stack developer building scalable web applications, REST APIs and cloud microservices",
    skills_must_have=["Python", "React", "Node.js", "JavaScript", "AWS", "Docker", "SQL", "MongoDB", "TypeScript", "Kubernetes"],
    experience=[
        ExperienceEntry(
            company="TechCo",
            role="Full Stack Developer",
            bullets=[
                "Developed scalable backend services and REST APIs using Node.js and Python",
                "Built responsive frontend interfaces with React and TypeScript",
                "Deployed containerized microservices on AWS using Docker, Kubernetes and CI/CD pipelines",
                "Designed relational database schemas and optimized SQL queries for performance",
                "Collaborated with product and design teams in agile sprints",
            ],
        )
    ],
)


def main() -> None:
    db = SessionLocal()
    jobs = db.query(JobPosting).all()
    scored = sorted(
        ((score_job(REFERENCE_PROFILE, job, REFERENCE_RESUME), job) for job in jobs),
        key=lambda pair: -pair[0][0],
    )
    above = sum(1 for (score, _), _ in scored if score >= 50)
    print(f"{len(jobs)} scraped jobs vs reference software profile -> {above} above 50%")
    for (score, _), job in scored[:10]:
        flag = "MATCH" if score >= 50 else "     "
        print(f"  {flag} {score:5.1f}  {job.title[:46]:46} {job.company[:20]}")
    db.close()


if __name__ == "__main__":
    main()
