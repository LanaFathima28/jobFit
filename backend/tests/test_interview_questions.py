import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.match import Match
from app.services.interview_questions import (
    generate_interview_questions,
    _validate_interview_grounding,
    _generate_fallback_interview_questions,
)

client = TestClient(app)


def test_generate_fallback_interview_questions():
    cand_data = {
        "full_name": "Jane Doe",
        "skills": ["Python", "FastAPI"],
        "total_years_experience": 3.0,
        "work_history": [{"title": "Software Engineer", "company": "Acme Corp"}]
    }
    job_data = {
        "job_title": "Senior Backend Developer",
        "required_skills": ["Python", "FastAPI", "AWS"],
        "min_years_experience": 5.0
    }
    hybrid_breakdown = {
        "breakdown": {
            "skills": {"matched_required_skills": ["Python", "FastAPI"], "missing_required_skills": ["AWS"]},
            "experience": {"candidate_years": 3.0, "required_years": 5.0, "status": "underqualified"}
        }
    }

    questions = _generate_fallback_interview_questions("Jane Doe", "Senior Backend Developer", cand_data, job_data, hybrid_breakdown)

    assert "technical_questions" in questions
    assert "behavioral_questions" in questions
    assert "gap_probing_questions" in questions
    assert len(questions["technical_questions"]) >= 1
    assert len(questions["gap_probing_questions"]) >= 1
    assert "AWS" in questions["gap_probing_questions"][0]["target_gap"]


def test_validate_interview_grounding_clean():
    cand_data = {"skills": ["Python", "PostgreSQL"]}
    job_data = {"required_skills": ["Python", "FastAPI"], "preferred_skills": []}

    questions_dict = {
        "technical_questions": [{"question": "Walk me through Python query design.", "target_skill": "Python"}],
        "behavioral_questions": [{"question": "Describe a conflict situation.", "focus_area": "Collaboration"}],
        "gap_probing_questions": [{"question": "How do you learn new tools?", "target_gap": "FastAPI"}]
    }

    warnings = _validate_interview_grounding(questions_dict, cand_data, job_data)
    assert warnings == []


def test_validate_interview_grounding_detects_unlisted_target():
    cand_data = {"skills": ["Python"]}
    job_data = {"required_skills": ["Python"], "preferred_skills": []}

    questions_dict = {
        "technical_questions": [{"question": "Explain Rust memory management.", "target_skill": "Rust"}],
        "behavioral_questions": [],
        "gap_probing_questions": []
    }

    warnings = _validate_interview_grounding(questions_dict, cand_data, job_data)
    assert len(warnings) > 0
    assert "Rust" in warnings[0]


@patch("app.services.interview_questions._call_claude_tool_use")
def test_generate_interview_questions_mocked_llm_success(mock_claude):
    mock_tool_output = {
        "technical_questions": [
            {"question": "At TechCorp, how did you architect Python microservices?", "target_skill": "Python", "context_reference": "TechCorp"}
        ],
        "behavioral_questions": [
            {"question": "How did your responsibilities change when promoted to Lead?", "focus_area": "Seniority jump"}
        ],
        "gap_probing_questions": [
            {"question": "How would you apply your Docker experience to AWS?", "target_gap": "AWS", "probing_strategy": "Container transfer"}
        ]
    }
    mock_claude.return_value = ("[Tool Output]", mock_tool_output)

    with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
        questions, status_str, raw_llm = generate_interview_questions(
            candidate_name="Alice Smith",
            job_title="Senior Engineer",
            candidate_structured_data={"skills": ["Python", "Docker"]},
            job_structured_data={"required_skills": ["Python", "AWS"]},
            hybrid_breakdown={"breakdown": {"skills": {"matched_required_skills": ["Python"], "missing_required_skills": ["AWS"]}}}
        )

        assert status_str == "success"
        assert len(questions["technical_questions"]) == 1
        assert questions["technical_questions"][0]["target_skill"] == "Python"


@pytest.fixture
def sample_match_fixture():
    db = SessionLocal()
    job = Job(
        title="Senior Python Backend Engineer",
        description_text="Senior Python Backend Engineer description.",
        structured_data={
            "job_title": "Senior Python Backend Engineer",
            "required_skills": ["Python", "FastAPI"],
            "min_years_experience": 5.0
        }
    )
    cand = Candidate(
        name="Alex Mercer",
        raw_text="Experienced Python Developer with 6 years experience.",
        structured_data={
            "full_name": "Alex Mercer",
            "skills": ["Python", "FastAPI"],
            "total_years_experience": 6.0,
            "work_history": [{"title": "Senior Developer", "company": "CloudInc"}]
        }
    )
    db.add(job)
    db.add(cand)
    db.commit()
    db.refresh(job)
    db.refresh(cand)

    match = Match(
        job_id=job.id,
        candidate_id=cand.id,
        final_score=92.0,
        semantic_score=90.0,
        skill_overlap_score=100.0,
        experience_score=100.0,
        education_score=100.0,
        score_breakdown={
            "final_score": 92.0,
            "breakdown": {
                "skills": {"matched_required_skills": ["Python", "FastAPI"], "missing_required_skills": []},
                "experience": {"candidate_years": 6.0, "required_years": 5.0, "status": "qualified"}
            }
        }
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    yield match, job, cand

    db.query(Match).filter(Match.id == match.id).delete()
    db.query(Candidate).filter(Candidate.id == cand.id).delete()
    db.query(Job).filter(Job.id == job.id).delete()
    db.commit()
    db.close()


def test_single_match_generate_questions_endpoint(sample_match_fixture):
    match, job, cand = sample_match_fixture

    response = client.post(f"/api/matches/{match.id}/generate-questions")
    assert response.status_code == 200

    data = response.json()
    assert data["match_id"] == str(match.id)
    assert "interview_questions" in data
    assert "technical_questions" in data["interview_questions"]
    assert "behavioral_questions" in data["interview_questions"]
    assert "gap_probing_questions" in data["interview_questions"]

    # Verify cached on second call
    res2 = client.post(f"/api/matches/{match.id}/generate-questions")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "cached"


def test_get_single_match_endpoint(sample_match_fixture):
    match, job, cand = sample_match_fixture

    # Generate questions first
    client.post(f"/api/matches/{match.id}/generate-questions")

    # Fetch match details via GET
    res = client.get(f"/api/matches/{match.id}")
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(match.id)
    assert data["final_score"] == 92.0
    assert "interview_questions" in data
    assert data["interview_questions"] is not None


def test_batch_generate_questions_endpoint(sample_match_fixture):
    match, job, cand = sample_match_fixture

    res = client.post(f"/api/jobs/{job.id}/generate-questions-batch?top_n=5")
    assert res.status_code == 200

    data = res.json()
    assert data["job_id"] == str(job.id)
    assert data["total_target_matches"] >= 1
    assert len(data["results"]) >= 1
    assert "interview_questions" in data["results"][0]
