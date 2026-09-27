from datetime import datetime
from uuid import UUID
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    title: str
    description_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    extraction_status: Optional[str] = "pending"
    extraction_error: Optional[str] = None
    structured_extraction_status: Optional[str] = "pending"
    debug_raw_llm_output: Optional[str] = None
    embedding_input: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: UUID
    embedding: Optional[List[float]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateMatchResponse(BaseModel):
    id: UUID
    name: str
    final_score: float
    similarity_score: float
    semantic_score: Optional[float] = None
    skill_overlap_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    weights_used: Optional[Dict[str, float]] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    explanation: Optional[Any] = None
    interview_questions: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None


    structured_data: Optional[Dict[str, Any]] = None
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    extraction_status: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
