import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import io

from app.main import app
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.match import Match
from app.worker.tasks import process_job_pipeline_task, process_candidate_file_pipeline_task

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_standardized_error_format_404():
    """
    Verify 404 errors return standard error JSON shape.
    """
    response = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "Job not found" in data["error"]["message"]


def test_standardized_error_format_400():
    """
    Verify 400 errors return standard error JSON shape.
    """
    response = client.post("/api/candidates/upload", files=[("file", ("bad.txt", b"some content", "text/plain"))])
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "BAD_REQUEST"


@patch("app.worker.tasks.generate_text_embedding")
@patch("app.worker.tasks.extract_candidate_structured_data")
@patch("app.worker.tasks.extract_job_structured_data")
@patch("app.worker.tasks.generate_candidate_explanation")
@patch("app.worker.tasks.generate_interview_questions")
def test_full_pipeline_orchestration_end_to_end(
    mock_questions,
    mock_explain,
    mock_extract_job,
    mock_extract_cand,
    mock_embed,
    db_session
):
    """
    Integration test running a full pipeline end-to-end:
    upload candidates -> process job pipeline -> poll status -> confirm match with score, explanation, and questions.
    """
    # Mocks
    mock_embed.return_value = [0.1] * 1536
    mock_extract_job.return_value = (
        {"job_title": "Senior Python Engineer", "skills": ["Python", "FastAPI"], "min_experience_years": 4},
        "success",
        "raw llm"
    )
    mock_extract_cand.return_value = (
        {"full_name": "Alice Innovator", "skills": ["Python", "FastAPI"], "total_years_experience": 5.0},
        "success",
        "raw llm"
    )
    mock_explain.return_value = (
        {"summary": "Alice is a strong candidate with 5 years experience.", "pros": ["Python expert"]},
        "success",
        "raw llm"
    )
    mock_questions.return_value = (
        {
            "technical_questions": [{"question": "Explain Python GIL.", "target_skill": "Python"}],
            "behavioral_questions": [],
            "gap_probing_questions": []
        },
        "success",
        "raw llm"
    )

    db_session.query(Match).delete()
    db_session.query(Candidate).delete()
    db_session.query(Job).delete()
    db_session.commit()

    # 1. Create Job
    job = Job(
        title="Senior Python Engineer",
        description_text="Looking for a Senior Python Engineer with FastAPI experience.",
        extraction_status="success"
    )
    db_session.add(job)

    # 2. Create Candidate
    cand = Candidate(
        name="Alice Innovator",
        raw_text="Alice Innovator resume with 5 years Python and FastAPI experience.",
        extraction_status="success"
    )
    db_session.add(cand)
    db_session.commit()

    try:
        # 3. Trigger Job Processing Endpoint
        response = client.post(f"/api/jobs/{job.id}/process?top_n_explain=5&top_n_questions=5")
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["job_id"] == str(job.id)
        assert data["status"] == "processing"

        task_id = data["task_id"]

        # Run worker task synchronously to simulate Celery worker execution
        summary = process_job_pipeline_task.run(str(job.id), top_n_explain=5, top_n_questions=5)
        assert summary["status"] == "success"
        assert summary["ranked_matches_count"] >= 1

        # 4. Poll Task Status Endpoint
        status_res = client.get(f"/api/tasks/{task_id}/status")
        assert status_res.status_code == 200

        # 5. Fetch Ranked Matches & Confirm final match details
        matches_res = client.get(f"/api/jobs/{job.id}/matches")
        assert matches_res.status_code == 200
        matches_data = matches_res.json()
        assert len(matches_data) == 1
        top_match = matches_data[0]
        assert top_match["name"] == "Alice Innovator"
        assert top_match["final_score"] > 0
        assert top_match["explanation"] is not None
        assert top_match["interview_questions"] is not None

    finally:
        db_session.query(Match).filter(Match.job_id == job.id).delete()
        db_session.query(Candidate).filter(Candidate.id == cand.id).delete()
        db_session.query(Job).filter(Job.id == job.id).delete()
        db_session.commit()


@patch("app.worker.tasks.generate_text_embedding")
@patch("app.worker.tasks.extract_candidate_structured_data")
@patch("app.worker.tasks.extract_job_structured_data")
def test_pipeline_partial_failure_resilience(
    mock_extract_job,
    mock_extract_cand,
    mock_embed,
    db_session
):
    """
    Test that a failure partway through the pipeline (e.g. one candidate's extraction fails)
    doesn't block the rest of the batch.
    """
    mock_embed.return_value = [0.1] * 1536
    mock_extract_job.return_value = ({"job_title": "Backend Dev", "skills": ["Python"]}, "success", "")

    # Side effect: first candidate succeeds, second candidate raises exception
    def extract_cand_side_effect(text):
        if "Corrupt" in text:
            raise Exception("PDF parsing error: Corrupted stream")
        return ({"full_name": "Valid Candidate", "skills": ["Python"]}, "success", "")

    mock_extract_cand.side_effect = extract_cand_side_effect

    # Clean up any leftover records from prior test runs to ensure isolation
    db_session.query(Match).delete()
    db_session.query(Candidate).delete()
    db_session.query(Job).delete()
    db_session.commit()

    job = Job(title="Backend Dev", description_text="Python Backend Developer description.")
    db_session.add(job)

    valid_cand = Candidate(name="Valid Candidate", raw_text="Valid resume content with Python.")
    corrupt_cand = Candidate(name="Corrupt Candidate", raw_text="Corrupt file raw text content.")
    db_session.add(valid_cand)
    db_session.add(corrupt_cand)
    db_session.commit()

    try:
        # Run pipeline task synchronously
        summary = process_job_pipeline_task.run(str(job.id))
        assert summary["status"] == "success"
        assert summary["failed_candidates"] == 1
        assert summary["processed_candidates"] == 1

        # Check DB states
        db_session.refresh(valid_cand)
        db_session.refresh(corrupt_cand)
        assert valid_cand.structured_extraction_status == "success"
        assert corrupt_cand.structured_extraction_status == "failed"

    finally:
        db_session.query(Match).filter(Match.job_id == job.id).delete()
        db_session.query(Candidate).filter(Candidate.id.in_([valid_cand.id, corrupt_cand.id])).delete()
        db_session.query(Job).filter(Job.id == job.id).delete()
        db_session.commit()
