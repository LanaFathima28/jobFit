#!/usr/bin/env python3
"""
Manual-review quality testing script for Phase 5: Candidate Match Explanation Generator.
Generates explanations for 5-6 sample candidates with distinct score profiles (high, mid, low, overqualified).
Allows inspecting output specificity, tone calibration, JSON structure, and grounding validation.
"""

import sys
import os
import json

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scoring import calculate_hybrid_score
from app.services.explanation import generate_candidate_explanation, _validate_explanation_grounding


def run_explanation_quality_check():
    job_title = "Senior Python Backend Engineer"
    job_structured = {
        "job_title": job_title,
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Redis"],
        "min_years_experience": 5.0,
        "education_requirement": "Bachelor of Science in Computer Science"
    }

    candidates = [
        {
            "name": "Alice Smith (High Match - 94%)",
            "structured_data": {
                "full_name": "Alice Smith",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                "total_years_experience": 6.0,
                "education": [{"degree": "Bachelor of Science in Computer Science"}]
            },
            "semantic_score": 0.85
        },
        {
            "name": "Bob Miller (Mid Match - 72%)",
            "structured_data": {
                "full_name": "Bob Miller",
                "skills": ["Python", "PostgreSQL"],  # Missing FastAPI required
                "total_years_experience": 4.0,       # Slightly under 5 years
                "education": [{"degree": "Bachelor of Science in Information Tech"}]
            },
            "semantic_score": 0.65
        },
        {
            "name": "Charlie Davis (Low Match - 38%)",
            "structured_data": {
                "full_name": "Charlie Davis",
                "skills": ["Java", "HTML", "CSS"],   # 0 required skills matched!
                "total_years_experience": 2.0,       # Significantly underqualified
                "education": [{"degree": "Associate Degree"}]
            },
            "semantic_score": 0.30
        },
        {
            "name": "Diana Prince (Overqualified Match - 88%)",
            "structured_data": {
                "full_name": "Diana Prince",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "AWS"],
                "total_years_experience": 15.0,      # Overqualified (> 5 + 3 yrs)
                "education": [{"degree": "Master of Science in Software Engineering"}]
            },
            "semantic_score": 0.80
        },
        {
            "name": "Evan Wright (Frontend Specialist - 42%)",
            "structured_data": {
                "full_name": "Evan Wright",
                "skills": ["React", "TypeScript", "Tailwind CSS"], # Mismatched tech stack
                "total_years_experience": 5.0,
                "education": [{"degree": "Bachelor of Arts in Graphic Design"}]
            },
            "semantic_score": 0.35
        }
    ]

    print("\n" + "=" * 110)
    print("PHASE 5: CANDIDATE MATCH EXPLANATION QUALITY & TONE EVALUATION")
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

        final_score = hybrid_res["final_score"]

        explanation, status_str, raw_llm = generate_candidate_explanation(
            candidate_name=name,
            job_title=job_title,
            final_score=final_score,
            hybrid_breakdown=hybrid_res
        )

        grounding_warnings = _validate_explanation_grounding(explanation, hybrid_res)

        print("-" * 110)
        print(f"CANDIDATE: {name}")
        print(f"SCORE: Final={final_score}%, Skills={hybrid_res['skill_overlap_score']}%, Exp={hybrid_res['experience_score']}%, Edu={hybrid_res['education_score']}%")
        print(f"GENERATION STATUS: {status_str}")
        print(f"VERDICT: {explanation.get('verdict')}")
        print(f"SUMMARY:\n{explanation.get('summary')}\n")
        print(f"STRENGTHS ({len(explanation.get('strengths', []))}):")
        for s in explanation.get('strengths', []):
            print(f"  + {s}")
        print(f"GAPS ({len(explanation.get('gaps', []))}):")
        for g in explanation.get('gaps', []):
            print(f"  - {g}")

        if grounding_warnings:
            print("GROUNDING WARNINGS:")
            for w in grounding_warnings:
                print(f"  ! {w}")
        else:
            print("GROUNDING CHECK: Passed (All mentioned skills are grounded in candidate dataset)")

    print("\n" + "=" * 110 + "\n")


if __name__ == "__main__":
    run_explanation_quality_check()
