import pytest
from app.services.scoring import (
    calculate_skill_overlap_score,
    calculate_experience_score,
    calculate_education_score,
    calculate_hybrid_score,
)


def test_skill_overlap_score_exact_match():
    cand_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    job_req_skills = ["Python", "FastAPI"]
    job_pref_skills = ["Docker"]

    score, detail = calculate_skill_overlap_score(cand_skills, job_req_skills, job_pref_skills)

    assert score == 1.0
    assert set(detail["matched_required_skills"]) == {"Python", "FastAPI"}
    assert detail["missing_required_skills"] == []
    assert detail["matched_preferred_skills"] == ["Docker"]
    assert detail["missing_preferred_skills"] == []


def test_skill_overlap_score_partial_match():
    cand_skills = ["Python", "Git"]
    job_req_skills = ["Python", "FastAPI"]
    job_pref_skills = ["Docker"]

    score, detail = calculate_skill_overlap_score(cand_skills, job_req_skills, job_pref_skills)

    # 1 of 2 required (0.5 ratio * 0.75 = 0.375)
    # 0 of 1 preferred (0.0 ratio * 0.25 = 0.0)
    # Total = 0.375
    assert score == 0.375
    assert detail["matched_required_skills"] == ["Python"]
    assert detail["missing_required_skills"] == ["FastAPI"]
    assert detail["missing_preferred_skills"] == ["Docker"]



def test_skill_overlap_empty_candidate_skills():
    cand_skills = []
    job_req_skills = ["Python", "FastAPI"]

    score, detail = calculate_skill_overlap_score(cand_skills, job_req_skills)

    assert score == 0.0
    assert detail["matched_required_skills"] == []
    assert len(detail["missing_required_skills"]) == 2


def test_skill_overlap_no_job_skills_required():
    cand_skills = ["Python"]
    job_req_skills = []

    score, detail = calculate_skill_overlap_score(cand_skills, job_req_skills)

    assert score == 1.0


def test_experience_score_underqualified():
    # 3 years candidate vs 5 years required -> 3/5 = 0.6
    score, detail = calculate_experience_score(3.0, 5.0)

    assert score == 0.6
    assert detail["status"] == "underqualified"
    assert detail["overqualified_flag"] is False


def test_experience_score_exact_and_within_margin():
    # Exact required match
    score1, detail1 = calculate_experience_score(5.0, 5.0)
    assert score1 == 1.0
    assert detail1["status"] == "qualified"

    # Within 3 years above required (e.g. 7 years for 5-year requirement)
    score2, detail2 = calculate_experience_score(7.5, 5.0)
    assert score2 == 1.0
    assert detail2["status"] == "qualified"
    assert detail2["overqualified_flag"] is False


def test_experience_score_overqualified():
    # 10 years for 5-year requirement: excess = 10 - (5 + 3) = 2 years.
    # Score = max(0.70, 1.0 - (0.03 * 2)) = 0.94
    score, detail = calculate_experience_score(10.0, 5.0)

    assert score == 0.94
    assert detail["status"] == "overqualified"
    assert detail["overqualified_flag"] is True


def test_experience_score_wildly_overqualified_floor():
    # 25 years for 3-year requirement: decay hits floor at 0.70
    score, detail = calculate_experience_score(25.0, 3.0)

    assert score == 0.70
    assert detail["status"] == "overqualified"
    assert detail["overqualified_flag"] is True


def test_experience_score_no_requirement():
    score, detail = calculate_experience_score(8.0, 0.0)

    assert score == 1.0
    assert detail["status"] == "qualified"
    assert detail["overqualified_flag"] is False


def test_education_score_meets_or_exceeds():
    cand_edu = [{"degree": "Master of Science in Computer Science"}]
    job_req = "Bachelor of Science in CS"

    score, detail = calculate_education_score(cand_edu, job_req)

    assert score == 1.0
    assert detail["status"] == "meets_or_exceeds"


def test_education_score_one_level_below():
    cand_edu = [{"degree": "Associate Degree in Information Technology"}]
    job_req = "Bachelor's Degree"

    score, detail = calculate_education_score(cand_edu, job_req)

    assert score == 0.80
    assert detail["status"] == "one_level_below"


def test_education_score_below_requirement():
    cand_edu = []
    job_req = "Master of Science"

    score, detail = calculate_education_score(cand_edu, job_req)

    assert score == 0.50
    assert detail["status"] == "below_requirement"


def test_education_score_unstated_job_requirement():
    cand_edu = [{"degree": "High School Diploma"}]
    
    score1, detail1 = calculate_education_score(cand_edu, None)
    assert score1 == 1.0
    assert detail1["status"] == "no_requirement_stated"

    score2, detail2 = calculate_education_score(cand_edu, "None")
    assert score2 == 1.0
    assert detail2["status"] == "no_requirement_stated"


def test_hybrid_score_calculation_default_weights():
    # Semantic: 0.80 (80%), Skills: 1.0 (100%), Exp: 1.0 (100%), Edu: 1.0 (100%)
    # Default weights: Skills 40%, Semantic 30%, Experience 20%, Education 10%
    # Expected: (0.40 * 1.0) + (0.30 * 0.80) + (0.20 * 1.0) + (0.10 * 1.0)
    # = 0.40 + 0.24 + 0.20 + 0.10 = 0.94 -> 94.0%

    cand_data = {
        "skills": ["Python", "FastAPI"],
        "total_years_experience": 5.0,
        "education": [{"degree": "Bachelor of Science"}]
    }
    job_data = {
        "required_skills": ["Python", "FastAPI"],
        "min_years_experience": 5.0,
        "education_requirement": "Bachelor of Science"
    }

    result = calculate_hybrid_score(
        semantic_score_0_to_1=0.80,
        candidate_structured_data=cand_data,
        job_structured_data=job_data
    )

    assert result["final_score"] == 94.0
    assert result["semantic_score"] == 80.0
    assert result["skill_overlap_score"] == 100.0
    assert result["experience_score"] == 100.0
    assert result["education_score"] == 100.0


def test_hybrid_score_custom_weights_override():
    # Heavy skills weight (70%), Semantic 10%, Exp 10%, Edu 10%
    custom_weights = {
        "skills_weight": 0.70,
        "semantic_weight": 0.10,
        "experience_weight": 0.10,
        "education_weight": 0.10
    }
    cand_data = {
        "skills": ["Python"],  # 1 of 2 -> 0.5 ratio
        "total_years_experience": 5.0,
        "education": [{"degree": "Bachelor"}]
    }
    job_data = {
        "required_skills": ["Python", "FastAPI"],
        "min_years_experience": 5.0,
        "education_requirement": "Bachelor"
    }

    result = calculate_hybrid_score(
        semantic_score_0_to_1=1.0,  # 100% semantic
        candidate_structured_data=cand_data,
        job_structured_data=job_data,
        weights=custom_weights
    )

    # Calculation: (0.70 * 0.5) + (0.10 * 1.0) + (0.10 * 1.0) + (0.10 * 1.0)
    # = 0.35 + 0.10 + 0.10 + 0.10 = 0.65 -> 65.0%
    assert result["final_score"] == 65.0
