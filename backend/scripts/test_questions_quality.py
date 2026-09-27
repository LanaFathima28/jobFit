#!/usr/bin/env python3
"""
Manual-review quality testing script for Phase 6: Tailored Interview Question Generator.
Generates categorized interview questions for 3-4 distinct candidate profiles:
1. High Scorer (Ideal match)
2. Candidate with notable skill gap (e.g., missing AWS / FastAPI)
3. Candidate with career transition (e.g. Data Analyst -> Senior Engineer)
"""

import sys
import os
import json

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scoring import calculate_hybrid_score
from app.services.interview_questions import (
    generate_interview_questions,
    _validate_interview_grounding
)


def run_question_quality_check():
    job_title = "Senior Python Backend Engineer"
    job_structured = {
        "job_title": job_title,
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AWS"],
        "min_years_experience": 5.0,
        "responsibilities": [
            "Design high-throughput REST APIs using FastAPI and Python",
            "Optimize PostgreSQL database schemas and complex queries",
            "Deploy containerized microservices to AWS cloud infrastructure"
        ]
    }

    candidates = [
        {
            "name": "Alice Smith (Strong Match)",
            "structured_data": {
                "full_name": "Alice Smith",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                "total_years_experience": 6.0,
                "work_history": [
                    {
                        "title": "Senior Python Developer",
                        "company": "TechCorp",
                        "start_date": "2021",
                        "end_date": "Present",
                        "description": "Architected FastAPI backend microservices and optimized PostgreSQL database queries handling 10k req/sec."
                    },
                    {
                        "title": "Software Engineer",
                        "company": "DataData",
                        "start_date": "2018",
                        "end_date": "2021",
                        "description": "Built Python REST services and managed Docker containers."
                    }
                ]
            },
            "semantic_score": 0.85
        },
        {
            "name": "Bob Miller (Skill Gap - Missing FastAPI & AWS)",
            "structured_data": {
                "full_name": "Bob Miller",
                "skills": ["Python", "Django", "PostgreSQL", "Linux"],
                "total_years_experience": 5.0,
                "work_history": [
                    {
                        "title": "Backend Engineer",
                        "company": "WebCorp",
                        "start_date": "2019",
                        "end_date": "Present",
                        "description": "Built monolithic Django web applications with PostgreSQL and deployed on Linux servers."
                    }
                ]
            },
            "semantic_score": 0.60
        },
        {
            "name": "Charlie Davis (Career Transition - Analyst to Engineer)",
            "structured_data": {
                "full_name": "Charlie Davis",
                "skills": ["Python", "SQL", "FastAPI", "Pandas"],
                "total_years_experience": 4.0,
                "work_history": [
                    {
                        "title": "Python Developer",
                        "company": "FinTech Inc",
                        "start_date": "2022",
                        "end_date": "Present",
                        "description": "Transitioned to building FastAPI internal microservices for financial risk analytics."
                    },
                    {
                        "title": "Data Analyst",
                        "company": "Global Analytics",
                        "start_date": "2020",
                        "end_date": "2022",
                        "description": "Wrote complex SQL queries and Python data pipeline scripts."
                    }
                ]
            },
            "semantic_score": 0.70
        }
    ]

    print("\n" + "=" * 110)
    print("PHASE 6: TAILORED INTERVIEW QUESTION GENERATION QUALITY EVALUATION")
    print("=" * 110)
    print(f"Target Job: '{job_title}'")
    print(f"Required Skills: {job_structured['required_skills']}, Min Exp: {job_structured['min_years_experience']} yrs\n")

    for cand in candidates:
        name = cand["name"]
        cand_data = cand["structured_data"]
        sim_score = cand["semantic_score"]

        hybrid_res = calculate_hybrid_score(
            semantic_score_0_to_1=sim_score,
            candidate_structured_data=cand_data,
            job_structured_data=job_structured
        )

        questions, status_str, raw_llm = generate_interview_questions(
            candidate_name=name,
            job_title=job_title,
            candidate_structured_data=cand_data,
            job_structured_data=job_structured,
            hybrid_breakdown=hybrid_res
        )

        grounding_warnings = _validate_interview_grounding(questions, cand_data, job_structured)

        print("-" * 110)
        print(f"CANDIDATE: {name}")
        print(f"SCORE: Final={hybrid_res['final_score']}%, Skills={hybrid_res['skill_overlap_score']}%, Exp={hybrid_res['experience_score']}%")
        print(f"GENERATION STATUS: {status_str}")

        print("\n1. TECHNICAL QUESTIONS:")
        for idx, q in enumerate(questions.get("technical_questions", []), 1):
            print(f"   {idx}. [Target: {q.get('target_skill')}] (Context: {q.get('context_reference', 'N/A')})")
            print(f"      Q: {q.get('question')}")

        print("\n2. BEHAVIORAL QUESTIONS:")
        for idx, q in enumerate(questions.get("behavioral_questions", []), 1):
            print(f"   {idx}. [Focus: {q.get('focus_area', 'General')}]")
            print(f"      Q: {q.get('question')}")

        print("\n3. GAP PROBING QUESTIONS:")
        for idx, q in enumerate(questions.get("gap_probing_questions", []), 1):
            print(f"   {idx}. [Target Gap: {q.get('target_gap')}] (Strategy: {q.get('probing_strategy', 'N/A')})")
            print(f"      Q: {q.get('question')}")

        if grounding_warnings:
            print("\nGROUNDING WARNINGS:")
            for w in grounding_warnings:
                print(f"   ! {w}")
        else:
            print("\nGROUNDING CHECK: Passed (All target skills & gaps match profile)")

    print("\n" + "=" * 110 + "\n")


if __name__ == "__main__":
    run_question_quality_check()
