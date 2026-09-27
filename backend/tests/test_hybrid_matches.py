import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.match import Match
from app.core.config import settings

client = TestClient(app)


@pytest.fixture
def sample_job_and_candidates():
    db = SessionLocal()
    # Create sample job
    job = Job(
        title="Full Stack Software Engineer",
        description_text="Looking for a Full Stack Engineer with 4+ years of Python and React experience. Bachelor's required.",
        structured_data={
            "job_title": "Full Stack Software Engineer",
            "required_skills": ["Python", "React"],
            "preferred_skills": ["Docker"],
            "min_years_experience": 4.0,
            "education_requirement": "Bachelor of Science"
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cand1 = Candidate(
        name="Candidate One (Strong match)",
        raw_text="Python and React developer with 5 years experience. BS in CS.",
        structured_data={
            "full_name": "Candidate One",
            "skills": ["Python", "React", "Docker"],
            "total_years_experience": 5.0,
            "education": [{"degree": "Bachelor of Science in Computer Science"}]
        }
    )
    cand2 = Candidate(
        name="Candidate Two (Weak match)",
        raw_text="Java developer with 1 year experience.",
        structured_data={
            "full_name": "Candidate Two",
            "skills": ["Java"],
            "total_years_experience": 1.0,
            "education": []
        }
    )
    db.add(cand1)
    db.add(cand2)
    db.commit()
    db.refresh(cand1)
    db.refresh(cand2)

    yield job, [cand1, cand2]

    # Cleanup
    db.query(Match).filter(Match.job_id == job.id).delete()
    db.query(Candidate).filter(Candidate.id.in_([cand1.id, cand2.id])).delete()
    db.query(Job).filter(Job.id == job.id).delete()
    db.commit()
    db.close()


def test_get_job_hybrid_matches(sample_job_and_candidates):
    job, candidates = sample_job_and_candidates
    url = f"/api/jobs/{job.id}/matches"

    response = client.get(url)
    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 2

    top_candidate = data[0]
    assert top_candidate["name"] == "Candidate One (Strong match)"
    assert "final_score" in top_candidate
    assert "skill_overlap_score" in top_candidate
    assert "experience_score" in top_candidate
    assert "education_score" in top_candidate
    assert "weights_used" in top_candidate
    assert "score_breakdown" in top_candidate

    # Check match DB record persisted
    db = SessionLocal()
    match_record = db.query(Match).filter(Match.job_id == job.id, Match.candidate_id == candidates[0].id).first()
    assert match_record is not None
    assert match_record.final_score is not None
    assert match_record.score_breakdown is not None
    db.close()


def test_get_job_hybrid_matches_query_weight_overrides(sample_job_and_candidates):
    job, _ = sample_job_and_candidates
    url = f"/api/v1/jobs/{job.id}/matches?skills_weight=0.80&semantic_weight=0.10&experience_weight=0.05&education_weight=0.05"

    response = client.get(url)
    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 1
    item = data[0]
    weights = item["weights_used"]

    assert abs(weights["skills_weight"] - 0.80) < 0.01
    assert abs(weights["semantic_weight"] - 0.10) < 0.01


def test_scoring_weights_config_endpoints():
    # GET default weights
    get_res = client.get("/api/config/scoring-weights")
    assert get_res.status_code == 200
    orig_weights = get_res.json()
    assert "skills_weight" in orig_weights

    # POST update weights
    new_weights = {
        "skills_weight": 0.50,
        "semantic_weight": 0.25,
        "experience_weight": 0.15,
        "education_weight": 0.10
    }
    post_res = client.post("/api/config/scoring-weights", json=new_weights)
    assert post_res.status_code == 200
    updated = post_res.json()
    assert updated["skills_weight"] == 0.50

    # Verify settings updated
    assert settings.DEFAULT_SKILLS_WEIGHT == 0.50

    # Restore original weights
    client.post("/api/config/scoring-weights", json=orig_weights)
