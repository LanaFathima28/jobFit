import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.embedding_service import (
    build_candidate_embedding_input,
    build_job_embedding_input,
    generate_text_embedding,
    compute_cosine_similarity,
)

# --- 1. Define 3 Distinct Job Descriptions ---

SAMPLE_JOBS = [
    {
        "id": "job_frontend",
        "title": "Senior React Frontend Engineer",
        "structured_data": {
            "job_title": "Senior React Frontend Engineer",
            "min_years_experience": 4.0,
            "required_skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "JavaScript"],
            "preferred_skills": ["GraphQL", "Web Vitals", "Jest"],
            "responsibilities": [
                "Build responsive web applications using React and Next.js.",
                "Optimize frontend performance, Core Web Vitals, and bundle size.",
                "Implement UI designs with Tailwind CSS and TypeScript."
            ]
        }
    },
    {
        "id": "job_data",
        "title": "Lead Data Platform Engineer",
        "structured_data": {
            "job_title": "Lead Data Platform Engineer",
            "min_years_experience": 6.0,
            "required_skills": ["Python", "PySpark", "Apache Spark", "Snowflake", "PostgreSQL", "SQL"],
            "preferred_skills": ["Airflow", "dbt", "AWS S3"],
            "responsibilities": [
                "Design and maintain large-scale ETL data pipelines.",
                "Optimize PySpark jobs and Snowflake data warehouse queries.",
                "Lead data platform architecture for analytics."
            ]
        }
    },
    {
        "id": "job_devops",
        "title": "DevOps & Cloud Infrastructure Architect",
        "structured_data": {
            "job_title": "DevOps & Cloud Infrastructure Architect",
            "min_years_experience": 5.0,
            "required_skills": ["AWS", "Kubernetes", "Terraform", "Docker", "CI/CD", "Ansible"],
            "preferred_skills": ["Prometheus", "Grafana", "Helm"],
            "responsibilities": [
                "Architect resilient AWS cloud infrastructure using Terraform.",
                "Manage Kubernetes clusters and automated CI/CD deployment pipelines.",
                "Ensure infrastructure security, monitoring, and compliance."
            ]
        }
    }
]


# --- 2. Define 5 Diverse Candidate Profiles ---

SAMPLE_CANDIDATES = [
    {
        "name": "Sarah Chen (Frontend Spec)",
        "structured_data": {
            "full_name": "Sarah Chen",
            "total_years_experience": 5.0,
            "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "JavaScript", "HTML", "CSS"],
            "work_history": [
                {"title": "Senior Frontend Developer", "company": "WebTech Inc", "description": "Built Next.js and React web apps with TypeScript."}
            ],
            "education": [{"degree": "B.S. Computer Science", "institution": "State Univ", "year": "2019"}]
        }
    },
    {
        "name": "Marcus Vance (Data Engineer)",
        "structured_data": {
            "full_name": "Marcus Vance",
            "total_years_experience": 7.0,
            "skills": ["Python", "PySpark", "Apache Spark", "Snowflake", "SQL", "PostgreSQL", "Airflow"],
            "work_history": [
                {"title": "Lead Data Engineer", "company": "DataCorp", "description": "Built PySpark data pipelines and managed Snowflake warehouse."}
            ],
            "education": [{"degree": "M.S. Data Science", "institution": "Tech Institute", "year": "2017"}]
        }
    },
    {
        "name": "David Miller (DevOps Architect)",
        "structured_data": {
            "full_name": "David Miller",
            "total_years_experience": 6.0,
            "skills": ["AWS", "Kubernetes", "Terraform", "Docker", "CI/CD", "Ansible", "Linux"],
            "work_history": [
                {"title": "Senior DevOps Engineer", "company": "CloudOps LLC", "description": "Automated AWS infrastructure with Terraform and managed Kubernetes."}
            ],
            "education": [{"degree": "B.S. Information Tech", "institution": "City College", "year": "2018"}]
        }
    },
    {
        "name": "Elena Rostova (Full Stack Generalist)",
        "structured_data": {
            "full_name": "Elena Rostova",
            "total_years_experience": 4.0,
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "Git"],
            "work_history": [
                {"title": "Full Stack Developer", "company": "AppSolutions", "description": "Developed Python FastAPI backends and React frontends."}
            ],
            "education": [{"degree": "B.S. Software Eng", "institution": "Polytechnic", "year": "2020"}]
        }
    },
    {
        "name": "Hiroshi Tanaka (Embedded C++ Dev)",
        "structured_data": {
            "full_name": "Hiroshi Tanaka",
            "total_years_experience": 8.0,
            "skills": ["C++", "C", "Microcontrollers", "RTOS", "Embedded Systems", "Assembly"],
            "work_history": [
                {"title": "Embedded Systems Engineer", "company": "Robotics Systems", "description": "Wrote C++ firmware for robotics microcontrollers."}
            ],
            "education": [{"degree": "B.S. Electrical Eng", "institution": "Tokyo Tech", "year": "2016"}]
        }
    }
]


def run_sanity_check():
    print("=" * 80)
    print("JOBFIT AI - PHASE 3 EMBEDDING & SEMANTIC MATCHING SANITY CHECK")
    print("=" * 80)
    print("Generating candidate embeddings...")

    # Build and generate embeddings for all 5 candidates
    candidate_records = []
    for cand in SAMPLE_CANDIDATES:
        emb_input = build_candidate_embedding_input(cand["structured_data"])
        vec = generate_text_embedding(emb_input)
        candidate_records.append({
            "name": cand["name"],
            "embedding_input": emb_input,
            "vector": vec
        })
    print(f"Successfully generated embeddings for {len(candidate_records)} candidates.\n")

    # Evaluate each job against all candidates
    for job in SAMPLE_JOBS:
        print("-" * 80)
        print(f"JOB ROLE: {job['title']}")
        job_input = build_job_embedding_input(job["structured_data"])
        job_vec = generate_text_embedding(job_input)

        matches = []
        for cand in candidate_records:
            score = compute_cosine_similarity(job_vec, cand["vector"])
            matches.append((cand["name"], score))

        # Sort descending by similarity score
        matches.sort(key=lambda x: x[1], reverse=True)

        print(f"{'Rank':<6} | {'Candidate Name':<35} | {'Cosine Sim Score':<15}")
        print("-" * 65)
        for rank, (cand_name, score) in enumerate(matches, 1):
            print(f"#{rank:<5} | {cand_name:<35} | {score:.4f}")

        top_score = matches[0][1]
        bottom_score = matches[-1][1]
        spread = top_score - bottom_score
        print(f"\n[ANALYSIS] Top Match: {matches[0][0]} ({top_score:.4f})")
        print(f"[ANALYSIS] Lowest Match: {matches[-1][0]} ({bottom_score:.4f})")
        print(f"[ANALYSIS] Score Spread: {spread:.4f}")
        if spread >= 0.15:
            print("[STATUS] EXCELLENT SCORE DIFFERENTIATION! High contrast between good vs bad matches.")
        else:
            print("[WARNING] Low score spread detected. Inspect embedding_input formatting.")
        print("\n")


if __name__ == "__main__":
    run_sanity_check()
