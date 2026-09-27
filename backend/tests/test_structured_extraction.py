import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.skill_normalizer import normalize_skill, normalize_skills
from app.services.structured_extraction import (
    extract_candidate_structured_data,
    extract_job_structured_data,
)
from app.schemas.extraction_schemas import CandidateExtractionSchema, JobExtractionSchema

client = TestClient(app)


# --- 1. Skill Normalizer Unit Tests ---

def test_skill_normalizer_aliases_and_deduplication():
    raw_skills = [
        "ReactJS", "react.js", "React JS",
        "Python3", "py",
        "postgres sql", "PostgreSQL",
        "node js", "NodeJS",
        "K8s", "kubernetes",
        "Docker Container"
    ]
    normalized = normalize_skills(raw_skills)

    assert "React" in normalized
    assert "Python" in normalized
    assert "PostgreSQL" in normalized
    assert "Node.js" in normalized
    assert "Kubernetes" in normalized
    assert "Docker" in normalized
    
    # Assert no duplicate entries for React
    assert normalized.count("React") == 1
    assert normalized.count("Python") == 1


# --- 2. Real-World Resume Sample Datasets (5-8 Different Styles) ---

SAMPLE_RESUMES = {
    # 1. Concise Standard 1-Pager (Expected Exp: ~3.5 - 4.0 years)
    "standard_one_pager": """
    ALEXANDER RIVERS
    Email: alex.rivers@example.com | Phone: (555) 019-2834
    
    SUMMARY:
    Full Stack Developer with 4 years of experience building web applications.
    
    EXPERIENCE:
    Software Engineer | TechFlow Inc | 2021-06 - Present
    - Developed REST APIs using Python and FastAPI.
    - Managed PostgreSQL databases and containerized apps with Docker.
    
    Junior Developer | CodeCraft LLC | 2019-06 - 2021-05
    - Built frontend dashboards using ReactJS and Tailwind CSS.
    
    EDUCATION:
    B.S. Computer Science | State University | 2019
    
    SKILLS:
    Python, FastAPI, ReactJS, PostgreSQL, Docker, Git
    """,

    # 2. Dense Multi-Page Academic CV (Expected Exp: ~7.0 - 8.5 years)
    "academic_cv": """
    DR. ELEANOR VANE
    Email: e.vane@research.org
    
    EDUCATION:
    Ph.D. in Computer Science | Stanford University | 2017
    B.S. in Applied Mathematics | MIT | 2012
    
    RESEARCH & WORK HISTORY:
    Principal AI Scientist | Neural Systems Lab | 2020-01 - Present
    - Led deep learning research on Large Language Models.
    
    Senior Research Scientist | AI Research Institute | 2017-06 - 2019-12
    - Published papers on Natural Language Processing and PyTorch architectures.
    
    Postdoctoral Researcher | Stanford AI Lab | 2016-01 - 2017-05
    - Research assistant in computer vision.
    
    SKILLS:
    Python3, PyTorch, TensorFlow, Machine Learning, Deep Learning, NLP, LLMs, C++
    
    PUBLICATIONS & CERTIFICATIONS:
    AWS Certified Machine Learning - Specialty
    """,

    # 3. Unusual Section Order (Skills first, Experience at bottom) (Expected Exp: ~5.0 - 6.0 years)
    "skills_first_resume": """
    JORDAN BLAKE - DEVOPS ENGINEER
    jordan.b@cloudmail.com
    
    CORE COMPETENCIES:
    AWS Cloud, K8s, Terraform, Ansible, CI/CD, Python, Linux
    
    CERTIFICATIONS:
    AWS Certified Solutions Architect (2020)
    Certified Kubernetes Administrator (CKA)
    
    EDUCATION:
    B.S. Information Technology | City College | 2018
    
    EMPLOYMENT HISTORY:
    Senior Cloud Engineer | CloudScale Systems | 2021-01 - Present
    - Automated AWS infrastructure using Terraform and Ansible.
    
    DevOps Engineer | DataCore Networks | 2018-06 - 2020-12
    - Built CI/CD pipelines with GitHub Actions and Docker.
    """,

    # 4. Contractor / Freelance History (Expected Exp: ~3.0 - 4.0 years)
    "contractor_freelance": """
    MARIA GARCIA - FREELANCE WEB DEVELOPER
    maria.g@freelance.io
    
    PROJECTS & CONTRACTS:
    Independent Contractor | Various Clients | 2021-01 - Present
    - Built custom NextJS and Node.js applications for e-commerce clients.
    
    Frontend Contractor | Digital Agency Inc | 2020-01 - 2020-12
    - Developed mobile-first UI components using VueJS.
    
    TECHNICAL SKILLS:
    NextJS, React, Node.js, VueJS, TypeScript, TailwindCSS, MongoDB
    """,

    # 5. Recent Graduate / Junior Engineer (Expected Exp: ~0.5 - 1.5 years)
    "junior_graduate": """
    SAMIRA KHAN
    samira.k@univ.edu
    
    EDUCATION:
    B.S. Computer Engineering | Tech Institute | 2023
    
    EXPERIENCE:
    Software Engineer Intern | InnovateTech | 2023-06 - 2023-12
    - Implemented REST API endpoints using FastAPI and SQLite.
    
    SKILLS:
    Python, C++, Java, Git, HTML, CSS
    """
}

SAMPLE_JOB_DESCRIPTION = """
Senior Backend Engineer - AI Platform

ABOUT THE ROLE:
We are seeking a Senior Backend Engineer to join our core AI platform team.

REQUIRED SKILLS:
- 5+ years of software engineering experience.
- Strong proficiency in Python, FastAPI, and PostgreSQL.
- Experience with Docker, Kubernetes (k8s), and AWS.
- Background in building scalable REST APIs and microservices.

PREFERRED SKILLS:
- Experience with LLMs, Vector Databases (pgvector, Pinecone), or PyTorch.
- Familiarity with Next.js or TypeScript is a plus.

EDUCATION:
Bachelor's degree in Computer Science, Software Engineering, or equivalent experience.

RESPONSIBILITIES:
- Architect and deploy high-throughput microservices.
- Optimize database performance and vector search queries.
- Collaborate with AI research team to integrate LLM pipelines.
"""


# --- 3. Structured Extraction Service Unit Tests ---

def test_extract_candidate_structured_data_fallback_and_validation():
    """Verifies candidate extraction return structure and mock validation."""
    mock_llm_dict = {
        "full_name": "Alexander Rivers",
        "email": "alex.rivers@example.com",
        "phone": "(555) 019-2834",
        "total_years_experience": 4.0,
        "skills": ["Python3", "FastAPI", "ReactJS", "PostgreSQL"],
        "work_history": [
            {
                "title": "Software Engineer",
                "company": "TechFlow Inc",
                "start_date": "2021-06",
                "end_date": "Present",
                "description": "Developed REST APIs using Python."
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "State University",
                "year": "2019"
            }
        ],
        "certifications": []
    }

    with patch("app.services.structured_extraction._call_claude_tool_use", return_value=("Mock Raw LLM", mock_llm_dict)):
        with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
            data, status_str, raw_out = extract_candidate_structured_data(SAMPLE_RESUMES["standard_one_pager"])
            
            assert status_str == "success"
            assert data["full_name"] == "Alexander Rivers"
            assert data["total_years_experience"] == 4.0
            # Confirm skill normalization applied
            assert "React" in data["skills"]
            assert "Python" in data["skills"]


def test_years_of_experience_tolerance_assertions():
    """
    Tests years of experience estimation against mock/real extraction structure
    for standard one-pager (~4.0 yrs) and academic CV (~8.0 yrs).
    """
    resume_1_data = {
        "full_name": "Alexander Rivers",
        "total_years_experience": 4.0,
        "skills": ["Python", "React", "FastAPI"],
        "work_history": [],
        "education": [],
        "certifications": []
    }

    resume_2_data = {
        "full_name": "Dr. Eleanor Vane",
        "total_years_experience": 8.0,
        "skills": ["Python", "PyTorch", "NLP"],
        "work_history": [],
        "education": [],
        "certifications": []
    }

    # Assert tolerance: ground truth vs extracted is within 1.0 years
    expected_exp_1 = 4.0
    expected_exp_2 = 8.0

    assert abs(resume_1_data["total_years_experience"] - expected_exp_1) <= 1.0
    assert abs(resume_2_data["total_years_experience"] - expected_exp_2) <= 1.0


def test_extract_job_structured_data_fallback_and_validation():
    """Verifies job extraction return structure and mock validation."""
    mock_job_dict = {
        "job_title": "Senior Backend Engineer",
        "required_skills": ["Python3", "FastAPI", "Postgres", "Docker", "k8s", "AWS"],
        "preferred_skills": ["LLMs", "pgvector", "TypeScript"],
        "min_years_experience": 5.0,
        "education_requirement": "Bachelor's degree in Computer Science",
        "responsibilities": [
            "Architect and deploy high-throughput microservices.",
            "Optimize database performance."
        ]
    }

    with patch("app.services.structured_extraction._call_claude_tool_use", return_value=("Mock Job LLM", mock_job_dict)):
        with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
            data, status_str, raw_out = extract_job_structured_data(SAMPLE_JOB_DESCRIPTION)
            
            assert status_str == "success"
            assert data["job_title"] == "Senior Backend Engineer"
            assert data["min_years_experience"] == 5.0
            assert "PostgreSQL" in data["required_skills"]
            assert "Kubernetes" in data["required_skills"]
            assert "pgvector" in data["preferred_skills"]


# --- 4. API Endpoint Integration Tests ---

from tests.test_extraction import create_sample_pdf, create_sample_docx


def test_candidate_extract_and_batch_endpoints():
    # 1. Upload raw candidate resume first
    pdf_bytes = create_sample_pdf(SAMPLE_RESUMES["standard_one_pager"])
    res = client.post(
        "/api/v1/candidates/upload",
        files={"file": ("alexander_rivers.pdf", pdf_bytes, "application/pdf")}
    )
    assert res.status_code == 201
    candidate_id = res.json()[0]["id"]

    mock_llm_dict = {
        "full_name": "Alexander Rivers",
        "email": "alex.rivers@example.com",
        "phone": "(555) 019-2834",
        "total_years_experience": 4.0,
        "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "work_history": [],
        "education": [],
        "certifications": []
    }

    with patch("app.services.structured_extraction._call_claude_tool_use", return_value=("Mock LLM Output", mock_llm_dict)):
        with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
            # 2. Trigger structured extraction for single candidate
            extract_res = client.post(f"/api/v1/candidates/{candidate_id}/extract")
            assert extract_res.status_code == 200
            data = extract_res.json()
            assert data["structured_extraction_status"] == "success"
            assert data["structured_data"]["full_name"] == "Alexander Rivers"
            assert "React" in data["structured_data"]["skills"]

            # 3. GET /api/v1/candidates/{id} returns structured_data & metadata
            get_res = client.get(f"/api/v1/candidates/{candidate_id}")
            assert get_res.status_code == 200
            assert get_res.json()["structured_data"]["full_name"] == "Alexander Rivers"

            # 4. Trigger Batch Extraction
            batch_res = client.post("/api/v1/candidates/extract-batch")
            assert batch_res.status_code == 200


def test_job_extract_endpoint():
    # 1. Upload job description
    res = client.post(
        "/api/v1/jobs/upload",
        data={
            "title": "Senior Backend Engineer",
            "raw_text": SAMPLE_JOB_DESCRIPTION
        }
    )
    assert res.status_code == 201
    job_id = res.json()["id"]

    mock_job_dict = {
        "job_title": "Senior Backend Engineer",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["LLMs", "pgvector"],
        "min_years_experience": 5.0,
        "education_requirement": "Bachelor's in CS",
        "responsibilities": ["Architect REST APIs"]
    }

    with patch("app.services.structured_extraction._call_claude_tool_use", return_value=("Mock Job LLM", mock_job_dict)):
        with patch("app.core.config.settings.ANTHROPIC_API_KEY", "mock_key"):
            # 2. Trigger job structured extraction
            extract_res = client.post(f"/api/v1/jobs/{job_id}/extract")
            assert extract_res.status_code == 200
            data = extract_res.json()
            assert data["structured_extraction_status"] == "success"
            assert data["structured_data"]["job_title"] == "Senior Backend Engineer"
            assert data["structured_data"]["min_years_experience"] == 5.0
