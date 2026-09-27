import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.embedding_service import (
    build_candidate_embedding_input,
    build_job_embedding_input,
    generate_text_embedding,
    generate_batch_embeddings,
    compute_cosine_similarity,
)
from tests.test_extraction import create_sample_pdf

client = TestClient(app)


def test_build_candidate_embedding_input():
    structured_data = {
        "full_name": "Alexander Rivers",
        "total_years_experience": 4.5,
        "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "work_history": [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "start_date": "2021-01",
                "end_date": "Present",
                "description": "Architected REST APIs using Python and FastAPI."
            }
        ],
        "education": [
            {"degree": "B.S. Computer Science", "institution": "State Univ", "year": "2020"}
        ]
    }

    inp = build_candidate_embedding_input(structured_data)

    assert "Alexander Rivers" in inp
    assert "Python, FastAPI, React, PostgreSQL" in inp
    assert "Senior Software Engineer at TechCorp" in inp
    assert "B.S. Computer Science" in inp


def test_build_job_embedding_input():
    structured_data = {
        "job_title": "Lead Python Developer",
        "min_years_experience": 5.0,
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "education_requirement": "Bachelor's in CS",
        "responsibilities": ["Design microservices", "Optimize SQL queries"]
    }

    inp = build_job_embedding_input(structured_data, title="Lead Python Developer")

    assert "Lead Python Developer" in inp
    assert "Minimum Experience Required: 5.0 years" in inp
    assert "Required Skills: Python, FastAPI, PostgreSQL" in inp
    assert "Preferred Skills: Docker, Kubernetes" in inp


def test_generate_text_embedding_and_batch():
    vec = generate_text_embedding("Python FastAPI Developer")
    assert len(vec) == 1536

    batch_vecs = generate_batch_embeddings(["Frontend Developer", "DevOps Engineer"])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 1536
    assert len(batch_vecs[1]) == 1536


def test_compute_cosine_similarity():
    vec_a = generate_text_embedding("Python FastAPI PostgreSQL")
    vec_b = generate_text_embedding("Python FastAPI PostgreSQL")
    vec_c = generate_text_embedding("Unrelated embedded microcontroller firmware")

    sim_identical = compute_cosine_similarity(vec_a, vec_b)
    sim_unrelated = compute_cosine_similarity(vec_a, vec_c)

    assert sim_identical >= 0.99
    assert sim_identical > sim_unrelated


def test_candidate_and_job_embedding_api_endpoints():
    # 1. Upload Candidate
    pdf_bytes = create_sample_pdf("Candidate: Jane Vance\nSkills: Python, FastAPI, Vector Search")
    cand_res = client.post(
        "/api/v1/candidates/upload",
        files={"file": ("jane_vance.pdf", pdf_bytes, "application/pdf")}
    )
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()[0]["id"]

    # 2. Embed Single Candidate
    embed_cand_res = client.post(f"/api/v1/candidates/{candidate_id}/embed")
    assert embed_cand_res.status_code == 200
    cand_data = embed_cand_res.json()
    assert cand_data["embedding_input"] is not None
    assert len(cand_data["embedding"]) == 1536

    # 3. Upload Job
    job_res = client.post(
        "/api/v1/jobs/upload",
        data={"title": "Python Engineer", "raw_text": "Seeking Python Engineer with FastAPI skills."}
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 4. Embed Single Job
    embed_job_res = client.post(f"/api/v1/jobs/{job_id}/embed")
    assert embed_job_res.status_code == 200
    job_data = embed_job_res.json()
    assert job_data["embedding_input"] is not None
    assert len(job_data["embedding"]) == 1536

    # 5. GET /api/v1/jobs/{job_id}/matches
    matches_res = client.get(f"/api/v1/jobs/{job_id}/matches?top_n=5")
    assert matches_res.status_code == 200
    matches_data = matches_res.json()
    assert isinstance(matches_data, list)
    assert len(matches_data) >= 1
    assert "similarity_score" in matches_data[0]
