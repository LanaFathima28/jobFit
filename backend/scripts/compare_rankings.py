#!/usr/bin/env python3
"""
CLI comparison script for Phase 4: Hybrid Scoring System.
Compares candidate rankings for a job under pure semantic similarity vs. hybrid scoring side-by-side.
Flags potential anomalies (e.g., candidates with 0 matching required skills ranking high).
"""

import sys
import os
import argparse
from typing import List, Dict, Any

# Add parent directory to sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.services.embedding_service import (
    build_candidate_embedding_input,
    build_job_embedding_input,
    generate_text_embedding,
    compute_cosine_similarity,
)
from app.services.scoring import calculate_hybrid_score, calculate_skill_overlap_score
from app.core.config import settings


def seed_demo_data_if_needed(db: Session) -> Job:
    """
    Seeds demo job and candidate records if database is empty.
    """
    existing_job = db.query(Job).first()
    if existing_job:
        return existing_job

    print("--> Database is empty. Seeding representative sample job and candidates for testing...")

    demo_job = Job(
        title="Senior Python Backend Engineer",
        description_text="We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, PostgreSQL, Redis, and Microservices. Bachelor's Degree in Computer Science required.",
        structured_data={
            "job_title": "Senior Python Backend Engineer",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker", "Redis", "Kubernetes"],
            "min_years_experience": 5.0,
            "education_requirement": "Bachelor of Science in Computer Science"
        }
    )
    db.add(demo_job)
    db.commit()
    db.refresh(demo_job)

    # Generate job embedding
    job_inp = build_job_embedding_input(demo_job.structured_data, demo_job.title, demo_job.description_text)
    demo_job.embedding_input = job_inp
    demo_job.embedding = generate_text_embedding(job_inp)
    db.commit()

    sample_candidates = [
        {
            "name": "Alice Smith (Ideal Match)",
            "raw_text": "Experienced Python Backend Developer with 6 years in FastAPI, PostgreSQL, Redis, Docker, and Kubernetes. Holds a Bachelor of Computer Science.",
            "structured_data": {
                "full_name": "Alice Smith",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
                "total_years_experience": 6.0,
                "education": [{"degree": "Bachelor of Science in Computer Science", "institution": "Tech Univ"}]
            }
        },
        {
            "name": "Bob Jones (Semantic match, missing skills)",
            "raw_text": "Software Developer with generic backend experience in Java, C++, and MySQL. Writes clean Python scripts for machine learning. 5 years experience.",
            "structured_data": {
                "full_name": "Bob Jones",
                "skills": ["Java", "C++", "MySQL", "Machine Learning"],
                "total_years_experience": 5.0,
                "education": [{"degree": "Bachelor of Science in Mathematics", "institution": "State College"}]
            }
        },
        {
            "name": "Charlie Brown (Junior, strong skills)",
            "raw_text": "Junior Python Developer with 1.5 years experience building APIs in Python, FastAPI, and PostgreSQL. Fast learner.",
            "structured_data": {
                "full_name": "Charlie Brown",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
                "total_years_experience": 1.5,
                "education": [{"degree": "Bachelor of Science in Computer Science", "institution": "City Univ"}]
            }
        },
        {
            "name": "Diana Prince (Overqualified Lead)",
            "raw_text": "Principal Architect with 14 years of software engineering experience in Python, FastAPI, PostgreSQL, Docker, AWS, and Distributed Systems.",
            "structured_data": {
                "full_name": "Diana Prince",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Architecture"],
                "total_years_experience": 14.0,
                "education": [{"degree": "Master of Science in Software Engineering", "institution": "Ivy League"}]
            }
        },
        {
            "name": "Evan Wright (Frontend Dev - Mismatch)",
            "raw_text": "Frontend Specialist with React, TypeScript, HTML, CSS, and Figma. 4 years of experience building modern web UIs.",
            "structured_data": {
                "full_name": "Evan Wright",
                "skills": ["React", "TypeScript", "HTML", "CSS", "Figma"],
                "total_years_experience": 4.0,
                "education": [{"degree": "Bachelor of Arts in Graphic Design", "institution": "Art Inst"}]
            }
        }
    ]

    for cand_info in sample_candidates:
        cand = Candidate(
            name=cand_info["name"],
            raw_text=cand_info["raw_text"],
            structured_data=cand_info["structured_data"]
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)

        cand_inp = build_candidate_embedding_input(cand.structured_data, cand.raw_text)
        cand.embedding_input = cand_inp
        cand.embedding = generate_text_embedding(cand_inp)
        db.commit()

    print("--> Seeding completed successfully.")
    return demo_job


def run_ranking_comparison(job_id_str: str = None, top_n: int = 10):
    db: Session = SessionLocal()
    try:
        if job_id_str:
            job = db.query(Job).filter(Job.id == job_id_str).first()
            if not job:
                print(f"Error: Job with ID '{job_id_str}' not found.")
                return
        else:
            job = seed_demo_data_if_needed(db)

        # Ensure job embedding exists
        if not job.embedding:
            job_inp = build_job_embedding_input(job.structured_data, job.title, job.description_text)
            job.embedding_input = job_inp
            job.embedding = generate_text_embedding(job_inp)
            db.commit()
            db.refresh(job)

        candidates = db.query(Candidate).all()
        if not candidates:
            print("No candidates found in database.")
            return

        # Calculate scores for each candidate
        evaluation_items = []
        for cand in candidates:
            if not cand.embedding:
                cand_inp = build_candidate_embedding_input(cand.structured_data, cand.raw_text)
                cand.embedding_input = cand_inp
                cand.embedding = generate_text_embedding(cand_inp)
                db.commit()
                db.refresh(cand)

            sim_raw = compute_cosine_similarity(job.embedding, cand.embedding)
            sim_score_pct = round(max(0.0, min(1.0, sim_raw)) * 100.0, 2)

            hybrid_res = calculate_hybrid_score(
                semantic_score_0_to_1=sim_raw,
                candidate_structured_data=cand.structured_data,
                job_structured_data=job.structured_data
            )

            matched_req_skills = hybrid_res["breakdown"]["skills"]["matched_required_skills"]
            missing_req_skills = hybrid_res["breakdown"]["skills"]["missing_required_skills"]
            total_req = len(matched_req_skills) + len(missing_req_skills)
            matched_count = len(matched_req_skills)

            evaluation_items.append({
                "candidate_id": cand.id,
                "name": cand.name,
                "semantic_score": sim_score_pct,
                "hybrid_score": hybrid_res["final_score"],
                "skill_overlap_score": hybrid_res["skill_overlap_score"],
                "experience_score": hybrid_res["experience_score"],
                "education_score": hybrid_res["education_score"],
                "matched_count": matched_count,
                "total_req": total_req,
                "matched_skills": matched_req_skills,
                "missing_skills": missing_req_skills,
                "exp_status": hybrid_res["breakdown"]["experience"]["status"],
                "overqualified": hybrid_res["breakdown"]["experience"]["overqualified_flag"]
            })

        # Rank candidates under Pure Semantic vs. Hybrid
        semantic_ranked = sorted(evaluation_items, key=lambda x: x["semantic_score"], reverse=True)
        for idx, item in enumerate(semantic_ranked, 1):
            item["semantic_rank"] = idx

        hybrid_ranked = sorted(evaluation_items, key=lambda x: x["hybrid_score"], reverse=True)
        for idx, item in enumerate(hybrid_ranked, 1):
            item["hybrid_rank"] = idx

        print("\n" + "=" * 110)
        print(f"JOB FIT HYBRID vs. SEMANTIC RANKING COMPARISON FOR: '{job.title}'")
        print("=" * 110)
        req_skills_str = ", ".join(job.structured_data.get("required_skills", [])) if job.structured_data else "None"
        min_exp_str = job.structured_data.get("min_years_experience", 0) if job.structured_data else 0
        print(f"Job Requirements: Skills=[{req_skills_str}], Min Exp={min_exp_str} yrs")
        print("Default Weights: Semantic=30%, Skills=40%, Experience=20%, Education=10%\n")

        print(f"{'HYBRID RANK':<12} | {'SEMANTIC RANK':<13} | {'CANDIDATE NAME':<32} | {'HYBRID':<7} | {'SEMANTIC':<8} | {'SKILLS':<7} | {'EXP':<6} | {'FLAGS':<20}")
        print("-" * 115)

        for item in hybrid_ranked[:top_n]:
            h_rank = f"#{item['hybrid_rank']}"
            s_rank = f"#{item['semantic_rank']}"
            name = item['name'][:30]
            h_score = f"{item['hybrid_score']:.1f}%"
            s_score = f"{item['semantic_score']:.1f}%"
            sk_score = f"{item['skill_overlap_score']:.1f}%"
            exp_score = f"{item['experience_score']:.1f}%"

            # Detect anomalies / flags
            flags = []
            if item["matched_count"] == 0 and item["total_req"] > 0:
                flags.append("ZERO_REQ_SKILLS")
            if item["overqualified"]:
                flags.append("OVERQUALIFIED")
            if item["exp_status"] == "underqualified":
                flags.append("UNDERQUALIFIED")
            
            rank_diff = item["semantic_rank"] - item["hybrid_rank"]
            if rank_diff >= 2:
                flags.append(f"PROMOTED (+{rank_diff})")
            elif rank_diff <= -2:
                flags.append(f"DEMOTED ({rank_diff})")

            flags_str = ", ".join(flags) if flags else "OK"

            print(f"{h_rank:<12} | {s_rank:<13} | {name:<32} | {h_score:<7} | {s_score:<8} | {sk_score:<7} | {exp_score:<6} | {flags_str:<20}")

        print("-" * 115)
        print("\nSUMMARY ANALYSIS & ANOMALY CHECKS:")
        for item in hybrid_ranked[:top_n]:
            if "ZERO_REQ_SKILLS" in [f for f in (item.get("flags") or [])] or (item["matched_count"] == 0 and item["total_req"] > 0):
                print(f" - WARNING ANOMALY: Candidate '{item['name']}' has 0/{item['total_req']} required skills! Semantic Score: {item['semantic_score']}%, Hybrid Score: {item['hybrid_score']}%. Ranked #{item['hybrid_rank']} overall.")
            elif item["hybrid_rank"] != item["semantic_rank"]:
                print(f" - RE-RANKING EFFECT: '{item['name']}' moved from #{item['semantic_rank']} (Semantic) -> #{item['hybrid_rank']} (Hybrid) due to rule sub-scores (Skills: {item['skill_overlap_score']}%, Exp: {item['experience_score']}%).")
        print("\n" + "=" * 110 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Pure Semantic vs. Hybrid Candidate Ranking")
    parser.add_argument("--job-id", type=str, help="UUID of Job record to test", default=None)
    parser.add_argument("--top-n", type=int, help="Number of top candidates to display", default=10)
    args = parser.parse_args()

    run_ranking_comparison(job_id_str=args.job_id, top_n=args.top_n)
