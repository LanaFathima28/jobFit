from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.schemas.candidate import CandidateResponse


class MatchBase(BaseModel):
    candidate_id: UUID
    job_id: UUID
    semantic_score: Optional[float] = None
    rule_score: Optional[float] = None
    skill_overlap_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    final_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    interview_questions: Optional[Dict[str, Any]] = None



class MatchCreate(MatchBase):
    pass


class MatchResponse(MatchBase):
    id: UUID
    created_at: datetime
    candidate: Optional[CandidateResponse] = None

    model_config = ConfigDict(from_attributes=True)


class MatchRankRequest(BaseModel):
    job_id: UUID
    candidate_ids: Optional[List[UUID]] = None


class MatchLeaderboardItem(BaseModel):
    id: UUID
    candidate_id: UUID
    candidate_name: str
    candidate_skills: List[str]
    candidate_experience_years: int
    job_id: UUID
    semantic_score: float
    rule_score: float
    final_score: float
    explanation: Optional[str] = None
    interview_questions: Optional[Dict[str, Any]] = None
    created_at: datetime


    model_config = ConfigDict(from_attributes=True)
