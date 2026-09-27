from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.services.interview_service import generate_tailored_interview_questions
from app.core.security import verify_api_key
from app.core.rate_limiter import check_rate_limit

router = APIRouter(prefix="/interviews", tags=["Interviews"])


class InterviewGenerateRequest(BaseModel):
    candidate_id: UUID
    job_id: UUID


@router.post("/generate", response_model=Dict[str, Any])
def generate_interview_kit(
    request: Request,
    payload: InterviewGenerateRequest,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Generate candidate-to-job gap analysis and tailored interview questions with rubrics.
    """
    check_rate_limit(request, limit=20, window_seconds=60)

    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidate_data = candidate.structured_data or {}
    job_data = job.structured_data or {}

    interview_kit = generate_tailored_interview_questions(
        candidate_name=candidate.name,
        candidate_data=candidate_data,
        job_title=job.title,
        job_data=job_data
    )

    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.name,
        "job_id": job.id,
        "job_title": job.title,
        "interview_kit": interview_kit
    }
