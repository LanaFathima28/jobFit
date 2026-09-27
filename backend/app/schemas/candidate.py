from datetime import datetime
from uuid import UUID
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict


class CandidateBase(BaseModel):
    name: str
    raw_text: Optional[str] = None
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


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: UUID
    embedding: Optional[List[float]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
