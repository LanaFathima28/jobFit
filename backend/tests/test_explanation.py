import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.match import Match
from app.services.explanation import (
    generate_candidate_explanation,
    _validate_explanation_grounding,
    _generate_fallback_explanation,
)

client = TestClient(app)


def test_generate_fallback_explanation():
    cand_name = "Jane Doe"
    job_title = "Backend Developer"
    final_score = 85.0
    hybrid_breakdown = {
        "semantic_score": 80.0,
        "skill_overlap_score": 100.0,
        "experience_score": 100.0,
        "education_score": 100.0,
        "breakdown": {
            "skills": {
                "matched_required_skills": ["Python", "FastAPI"],
                "missing_required_skills": [],
                "matched_preferred_skills": ["Docker"],
                "missing_preferred_skills": []
            },
            "experience": {
                "candidate_years": 5.0,
                "required_years": 3.0,
                "status": "qualified"
            },
            "education": {
                "candidate_degrees": ["Bachelor of Science"],
                "required_education": "Bachelor",
                "status": "meets_or_exceeds"
            }
        }
    }

    fallback = _generate_fallback_explanation(cand_name, job_title, final_score, hybrid_breakdown)

    assert "summary" in fallback
    assert "strengths" in fallback
    assert "gaps" in fallback
    assert "verdict" in fallback
    assert "85.0%" in fallback["verdict"] or "85.0%" in fallback["summary"]
    assert len(fallback["strengths"]) > 0


def test_validate_explanation_grounding_clean():
    hybrid_breakdown = {
        "breakdown": {
            "skills": {
                "matched_required_skills": ["Python", "FastAPI"],
                "missing_required_skills": ["PostgreSQL"],
                "matched_preferred_skills": [],
                "missing_preferred_skills": []
            }
        }
    }
    explanation_dict = {
        "summary": "Jane is proficient in Python and FastAPI but lacks PostgreSQL.",
        "strengths": ["Python experience"],
        "gaps": ["Missing PostgreSQL"],
        "verdict": "Good fit."
    }

    warnings = _validate_explanation_grounding(explanation_dict, hybrid_breakdown)
    assert warnings == []


def test_validate_explanation_grounding_detects_unlisted_skills():
    hybrid_breakdown = {
        "breakdown": {
            "skills": {
                "matched_required_skills": [],
                "missing_required_skills": [],
                "matched_preferred_skills": [],
                "missing_preferred_skills": []
            }
        }
    }
    explanation_dict = {
        "summary": "Candidate claims deep experience in Python, React, and AWS.",
        "strengths": ["AWS Cloud"],
        "gaps": [],
        "verdict": "Unverified."
    }

    warnings = _validate_explanation_grounding(explanation_dict, hybrid_breakdown)
    assert len(warnings) > 0
    assert "Grounding Warning" in warnings[0]


@patch("app.services.explanation._call_claude_tool_use")
def test_generate_candidate_explanation_mocked_llm_success(mock_claude):
    mock_tool_output = {
        "summary": "Alice Smith demonstrated strong skill overlap with Python and FastAPI, bringing 6 years of backend experience.",
        "strengths": ["Matched Python and FastAPI", "6 years experience exceeds 5-year requirement"],
        "gaps": ["Missing Kubernetes preferred skill"],
        "verdict": "Strong candidate match for Senior Engineer role."
    }
    mock_claude.return_value = ("[Tool Output]", mock_tool_output)

    with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
        explanation, status_str, raw_llm = generate_candidate_explanation(
            candidate_name="Alice Smith",
            job_title="Senior Engineer",
            final_score=92.0,
            hybrid_breakdown={
                "breakdown": {
                    "skills": {"matched_required_skills": ["Python", "FastAPI"]},
                    "experience": {"candidate_years": 6.0, "required_years": 5.0},
                    "education": {"status": "meets_or_exceeds"}
                }
            }
        )

        assert status_str == "success"
        assert explanation["summary"] == mock_tool_output["summary"]
        assert explanation["verdict"] == mock_tool_output["verdict"]


@pytest.fixture
def sample_match_fixture():
    db = SessionLocal()
    job = Job(
        title="DevOps Specialist",
        description_text="Docker and Kubernetes specialist needed.",
        structured_data={
            "job_title": "DevOps Specialist",
            "required_skills": ["Docker", "Kubernetes"],
            "min_years_experience": 3.0
        }
    )
    cand = Candidate(
        name="Sam Miller",
        raw_text="DevOps engineer with 4 years in Docker and Kubernetes.",
        structured_data={
            "full_name": "Sam Miller",
            "skills": ["Docker", "Kubernetes"],
            "total_years_experience": 4.0
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
        final_score=90.0,
        semantic_score=85.0,
        skill_overlap_score=100.0,
        experience_score=100.0,
        education_score=100.0,
        score_breakdown={
            "final_score": 90.0,
            "semantic_score": 85.0,
            "skill_overlap_score": 100.0,
            "experience_score": 100.0,
            "education_score": 100.0,
            "breakdown": {
                "skills": {"matched_required_skills": ["Docker", "Kubernetes"], "missing_required_skills": []},
                "experience": {"candidate_years": 4.0, "required_years": 3.0, "status": "qualified"},
                "education": {"status": "no_requirement_stated"}
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


def test_single_match_explain_endpoint(sample_match_fixture):
    match, job, cand = sample_match_fixture

    response = client.post(f"/api/matches/{match.id}/explain")
    assert response.status_code == 200

    data = response.json()
    assert data["match_id"] == str(match.id)
    assert data["candidate_name"] == "Sam Miller"
    assert "explanation" in data
    assert "summary" in data["explanation"]
    assert "verdict" in data["explanation"]

    # Verify DB match updated
    db = SessionLocal()
    db_match = db.query(Match).filter(Match.id == match.id).first()
    assert db_match.explanation is not None
    assert db_match.score_breakdown.get("explanation_object") is not None
    db.close()


def test_batch_match_explain_endpoint(sample_match_fixture):
    match, job, cand = sample_match_fixture

    response = client.post(f"/api/jobs/{job.id}/explain-batch")
    assert response.status_code == 200

    data = response.json()
    assert data["job_id"] == str(job.id)
    assert data["total_matches"] >= 1
    assert data["processed_count"] >= 1
    assert len(data["results"]) >= 1
    assert data["results"][0]["candidate_name"] == "Sam Miller"
