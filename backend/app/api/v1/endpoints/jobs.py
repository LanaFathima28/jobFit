import pathlib
from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import Job
from app.schemas.job import JobResponse, CandidateMatchResponse
from app.services.extraction_service import extract_text_from_file_bytes, ExtractionStatus
from app.services.storage import storage_service
from app.services.text_cleaner import clean_extracted_text
from app.core.security import verify_api_key
from app.core.rate_limiter import check_rate_limit
from app.worker.tasks import process_job_pipeline_task

router = APIRouter(prefix="/jobs", tags=["Jobs"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "text", "md"}


class JobCreatePayload(BaseModel):
    title: str
    description_text: str
    skills: Optional[List[str]] = []
    min_experience_years: Optional[int] = 0


class JobProcessResponse(BaseModel):
    task_id: str
    job_id: UUID
    status: str
    message: str


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_job_description(
    request: Request,
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Upload a job description via file (PDF, DOCX, TXT) OR raw text input.
    Extracts text, stores original file if provided, and saves job record with metadata.
    """
    check_rate_limit(request, limit=30, window_seconds=60)

    # Case 1: File Upload
    if file:
        filename = file.filename or "job_description.txt"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format '.{ext}'. Supported job description formats: PDF, DOCX, TXT."
            )

        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' exceeds 5MB size limit."
            )

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is empty (0 bytes)."
            )

        file_path, file_size = storage_service.save_file(file_bytes, filename, category="jobs")
        extraction_result = extract_text_from_file_bytes(file_bytes, filename)
        job_title = title or pathlib.Path(filename).stem.replace("_", " ").replace("-", " ").title()

        job = Job(
            title=job_title,
            description_text=extraction_result.text if extraction_result.status == ExtractionStatus.SUCCESS else None,
            original_filename=filename,
            file_type=ext,
            file_path=file_path,
            file_size=file_size,
            extraction_status=extraction_result.status.value,
            extraction_error=extraction_result.error_message
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    # Case 2: Direct Raw Text Input
    elif raw_text and raw_text.strip():
        cleaned_text = clean_extracted_text(raw_text)
        job_title = title or (cleaned_text.splitlines()[0][:100] if cleaned_text else "Untitled Job")

        job = Job(
            title=job_title,
            description_text=cleaned_text,
            original_filename=None,
            file_type="raw_text",
            file_path=None,
            file_size=len(raw_text.encode("utf-8")),
            extraction_status=ExtractionStatus.SUCCESS.value,
            extraction_error=None
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a job description file or raw_text input must be provided."
        )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job_json(
    payload: JobCreatePayload,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Create job posting from JSON payload (backwards compatibility).
    """
    if not payload.title or not payload.description_text:
        raise HTTPException(status_code=400, detail="Title and description_text are required.")

    cleaned_text = clean_extracted_text(payload.description_text)
    job = Job(
        title=payload.title,
        description_text=cleaned_text,
        file_type="raw_text",
        file_size=len(payload.description_text.encode("utf-8")),
        extraction_status=ExtractionStatus.SUCCESS.value
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    List all jobs with upload status.
    """
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get job details by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/{job_id}/process", response_model=JobProcessResponse, status_code=status.HTTP_202_ACCEPTED)
def process_job_full_pipeline(
    request: Request,
    job_id: UUID,
    top_n_explain: int = 10,
    top_n_questions: int = 5,
    skills_weight: Optional[float] = None,
    semantic_weight: Optional[float] = None,
    experience_weight: Optional[float] = None,
    education_weight: Optional[float] = None,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 7 Orchestration Endpoint: Runs the complete end-to-end matching pipeline for a job description.
    Triggers: Extract Job -> Embed Job -> Extract/Embed Candidates -> Compute Hybrid Scores -> Rank -> Generate AI Explanations & Questions for top N.
    Dispatches Celery background task and returns task_id immediately for polling via GET /api/tasks/{task_id}/status.
    """
    check_rate_limit(request, limit=20, window_seconds=60)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    weights_override = {}
    if skills_weight is not None:
        weights_override["skills_weight"] = skills_weight
    if semantic_weight is not None:
        weights_override["semantic_weight"] = semantic_weight
    if experience_weight is not None:
        weights_override["experience_weight"] = experience_weight
    if education_weight is not None:
        weights_override["education_weight"] = education_weight

    try:
        async_task = process_job_pipeline_task.delay(
            job_id_str=str(job_id),
            top_n_explain=top_n_explain,
            top_n_questions=top_n_questions,
            weights_override=weights_override if weights_override else None
        )
        task_id = async_task.id
    except Exception:
        import uuid
        task_id = str(uuid.uuid4())

    return JobProcessResponse(
        task_id=task_id,
        job_id=job.id,
        status="processing",
        message="Full job pipeline execution initiated asynchronously. Poll GET /api/tasks/{task_id}/status for progress."
    )


@router.post("/{job_id}/extract", response_model=JobResponse)
def extract_job_structured_data_endpoint(
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Triggers structured criteria extraction for a job description whose text is already stored.
    Saves extracted JSON to structured_data and updates structured_extraction_status and debug_raw_llm_output.
    """
    from app.services.structured_extraction import extract_job_structured_data

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.description_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job posting has no stored description_text to extract from."
        )

    structured_dict, ext_status, debug_llm = extract_job_structured_data(job.description_text)

    job.structured_data = structured_dict
    job.structured_extraction_status = ext_status
    job.debug_raw_llm_output = debug_llm

    if structured_dict.get("job_title") and structured_dict["job_title"].strip():
        job.title = structured_dict["job_title"].strip()

    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/embed", response_model=JobResponse)
def embed_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Generates and stores embedding_input and 1536-dim vector embedding for one job posting.
    """
    from app.services.embedding_service import build_job_embedding_input, generate_text_embedding

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    embedding_input = build_job_embedding_input(job.structured_data, job.title, job.description_text)
    vector = generate_text_embedding(embedding_input)

    job.embedding_input = embedding_input
    job.embedding = vector

    db.commit()
    db.refresh(job)
    return job


@router.post("/embed-batch", response_model=List[JobResponse])
def batch_embed_jobs_endpoint(
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Batch generates vector embeddings for all jobs without an embedding yet.
    """
    from app.services.embedding_service import build_job_embedding_input, generate_batch_embeddings

    unembedded_jobs = db.query(Job).filter(Job.embedding == None).all()
    if not unembedded_jobs:
        return []

    inputs = []
    for job in unembedded_jobs:
        inp = build_job_embedding_input(job.structured_data, job.title, job.description_text)
        job.embedding_input = inp
        inputs.append(inp)

    vectors = generate_batch_embeddings(inputs)
    for job, vec in zip(unembedded_jobs, vectors):
        job.embedding = vec

    db.commit()
    for job in unembedded_jobs:
        db.refresh(job)

    return unembedded_jobs


@router.get("/{job_id}/matches", response_model=List[CandidateMatchResponse])
def get_job_hybrid_candidate_matches(
    job_id: UUID,
    top_n: int = 10,
    skills_weight: Optional[float] = None,
    semantic_weight: Optional[float] = None,
    experience_weight: Optional[float] = None,
    education_weight: Optional[float] = None,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 4 Core Endpoint: Retrieves top N candidates for a job description ranked by hybrid scoring:
    combining semantic similarity with skill overlap, experience match, and education match sub-scores.
    Supports live per-request scoring weight overrides.
    """
    from app.core.config import settings
    from app.models.candidate import Candidate
    from app.models.match import Match
    from app.schemas.job import CandidateMatchResponse
    from app.services.embedding_service import (
        build_candidate_embedding_input,
        build_job_embedding_input,
        generate_text_embedding,
        compute_cosine_similarity,
    )
    from app.services.scoring import calculate_hybrid_score

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.embedding:
        inp = build_job_embedding_input(job.structured_data, job.title, job.description_text)
        job.embedding_input = inp
        job.embedding = generate_text_embedding(inp)
        db.commit()
        db.refresh(job)

    job_vector = job.embedding

    weights_override = {}
    weights_override["skills_weight"] = skills_weight if skills_weight is not None else settings.DEFAULT_SKILLS_WEIGHT
    weights_override["semantic_weight"] = semantic_weight if semantic_weight is not None else settings.DEFAULT_SEMANTIC_WEIGHT
    weights_override["experience_weight"] = experience_weight if experience_weight is not None else settings.DEFAULT_EXPERIENCE_WEIGHT
    weights_override["education_weight"] = education_weight if education_weight is not None else settings.DEFAULT_EDUCATION_WEIGHT

    candidates = db.query(Candidate).all()
    if not candidates:
        return []

    results = []
    for candidate in candidates:
        if not candidate.embedding:
            cand_inp = build_candidate_embedding_input(candidate.structured_data, candidate.raw_text)
            candidate.embedding_input = cand_inp
            candidate.embedding = generate_text_embedding(cand_inp)
            db.commit()
            db.refresh(candidate)

        raw_cosine_sim = compute_cosine_similarity(job_vector, candidate.embedding)

        hybrid_res = calculate_hybrid_score(
            semantic_score_0_to_1=raw_cosine_sim,
            candidate_structured_data=candidate.structured_data,
            job_structured_data=job.structured_data,
            weights=weights_override
        )

        existing_match = db.query(Match).filter(
            Match.candidate_id == candidate.id,
            Match.job_id == job.id
        ).first()

        if existing_match:
            existing_match.semantic_score = hybrid_res["semantic_score"]
            existing_match.rule_score = hybrid_res["rule_score"]
            existing_match.skill_overlap_score = hybrid_res["skill_overlap_score"]
            existing_match.experience_score = hybrid_res["experience_score"]
            existing_match.education_score = hybrid_res["education_score"]
            existing_match.final_score = hybrid_res["final_score"]
            existing_match.score_breakdown = hybrid_res
        else:
            new_match = Match(
                candidate_id=candidate.id,
                job_id=job.id,
                semantic_score=hybrid_res["semantic_score"],
                rule_score=hybrid_res["rule_score"],
                skill_overlap_score=hybrid_res["skill_overlap_score"],
                experience_score=hybrid_res["experience_score"],
                education_score=hybrid_res["education_score"],
                final_score=hybrid_res["final_score"],
                score_breakdown=hybrid_res
            )
            db.add(new_match)

        db.commit()

        explanation_obj = None
        questions_obj = None
        if existing_match:
            questions_obj = existing_match.interview_questions
            if existing_match.score_breakdown:
                explanation_obj = existing_match.score_breakdown.get("explanation_object") or existing_match.explanation
            elif existing_match.explanation:
                explanation_obj = existing_match.explanation

        match_item = CandidateMatchResponse(
            id=candidate.id,
            name=candidate.name,
            final_score=hybrid_res["final_score"],
            similarity_score=round(raw_cosine_sim, 4),
            semantic_score=hybrid_res["semantic_score"],
            skill_overlap_score=hybrid_res["skill_overlap_score"],
            experience_score=hybrid_res["experience_score"],
            education_score=hybrid_res["education_score"],
            weights_used=hybrid_res["weights_used"],
            score_breakdown=hybrid_res["breakdown"],
            explanation=explanation_obj,
            interview_questions=questions_obj,
            raw_text=candidate.raw_text,
            structured_data=candidate.structured_data,
            original_filename=candidate.original_filename,
            file_type=candidate.file_type,
            extraction_status=candidate.extraction_status,
            created_at=candidate.created_at
        )
        results.append(match_item)

    results.sort(key=lambda x: x.final_score, reverse=True)
    return results[:top_n]


@router.post("/{job_id}/explain-batch")
def generate_job_match_explanations_batch(
    request: Request,
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 5 Core Endpoint: Generates AI candidate match explanations for all candidate matches for a job description.
    Loop-structured for single batch operation, with partial failure resilience per candidate match.
    """
    check_rate_limit(request, limit=20, window_seconds=60)

    import logging
    from app.models.candidate import Candidate
    from app.models.match import Match
    from app.services.explanation import generate_candidate_explanation
    from app.services.scoring import calculate_hybrid_score

    logger = logging.getLogger(__name__)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    matches = db.query(Match).filter(Match.job_id == job_id).all()
    if not matches:
        return {"message": "No existing matches found for this job. Please run matches ranking first.", "processed_count": 0}

    processed_count = 0
    results = []

    for match in matches:
        candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
        if not candidate:
            continue

        hybrid_breakdown = match.score_breakdown or calculate_hybrid_score(
            semantic_score_0_to_1=(match.semantic_score or 0.0) / 100.0,
            candidate_structured_data=candidate.structured_data,
            job_structured_data=job.structured_data
        )

        try:
            explanation_dict, status_str, raw_llm = generate_candidate_explanation(
                candidate_name=candidate.name,
                job_title=job.title,
                final_score=match.final_score or 0.0,
                hybrid_breakdown=hybrid_breakdown
            )

            match.explanation = explanation_dict.get("summary")
            updated_breakdown = dict(hybrid_breakdown)
            updated_breakdown["explanation_object"] = explanation_dict
            updated_breakdown["explanation_status"] = status_str
            match.score_breakdown = updated_breakdown

            db.commit()
            processed_count += 1
            results.append({
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": status_str,
                "explanation": explanation_dict
            })
        except Exception as e:
            logger.error(f"Error generating explanation for candidate {candidate.id}: {str(e)}")
            results.append({
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": "failed",
                "error": str(e)
            })

    return {
        "job_id": str(job_id),
        "total_matches": len(matches),
        "processed_count": processed_count,
        "results": results
    }


@router.post("/{job_id}/generate-questions-batch")
def generate_job_match_interview_questions_batch(
    request: Request,
    job_id: UUID,
    top_n: int = 5,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 6 Core Endpoint: Generates tailored AI interview questions for top N candidate matches for a job description.
    Loop-structured batch operation with cost management (defaults to top_n=5) and partial failure resilience per match.
    """
    check_rate_limit(request, limit=20, window_seconds=60)

    import logging
    from app.models.candidate import Candidate
    from app.models.match import Match
    from app.services.interview_questions import generate_interview_questions
    from app.services.scoring import calculate_hybrid_score

    logger = logging.getLogger(__name__)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    matches = (
        db.query(Match)
        .filter(Match.job_id == job_id)
        .order_by(Match.final_score.desc())
        .limit(top_n)
        .all()
    )
    if not matches:
        return {"message": "No existing matches found for this job. Please run matches ranking first.", "processed_count": 0}

    processed_count = 0
    results = []

    for match in matches:
        candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
        if not candidate:
            continue

        if not regenerate and match.interview_questions:
            results.append({
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": "cached",
                "interview_questions": match.interview_questions
            })
            continue

        hybrid_breakdown = match.score_breakdown or calculate_hybrid_score(
            semantic_score_0_to_1=(match.semantic_score or 0.0) / 100.0,
            candidate_structured_data=candidate.structured_data,
            job_structured_data=job.structured_data
        )

        try:
            questions_dict, status_str, raw_llm = generate_interview_questions(
                candidate_name=candidate.name,
                job_title=job.title,
                candidate_structured_data=candidate.structured_data or {},
                job_structured_data=job.structured_data or {},
                hybrid_breakdown=hybrid_breakdown
            )

            match.interview_questions = questions_dict
            updated_breakdown = dict(hybrid_breakdown or {})
            updated_breakdown["interview_questions"] = questions_dict
            updated_breakdown["questions_status"] = status_str
            match.score_breakdown = updated_breakdown

            db.commit()
            processed_count += 1
            results.append({
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": status_str,
                "interview_questions": questions_dict
            })
        except Exception as e:
            logger.error(f"Error generating interview questions for candidate {candidate.id}: {str(e)}")
            results.append({
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": "failed",
                "error": str(e)
            })

    return {
        "job_id": str(job_id),
        "total_target_matches": len(matches),
        "processed_count": processed_count,
        "results": results
    }


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Delete job by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    db.delete(job)
    db.commit()
    return None
