from typing import Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.core.config import settings

router = APIRouter(prefix="/config", tags=["Configuration"])


class ScoringWeightsPayload(BaseModel):
    skills_weight: float = Field(0.40, ge=0.0, le=1.0)
    semantic_weight: float = Field(0.30, ge=0.0, le=1.0)
    experience_weight: float = Field(0.20, ge=0.0, le=1.0)
    education_weight: float = Field(0.10, ge=0.0, le=1.0)


@router.get("/scoring-weights", response_model=ScoringWeightsPayload)
def get_scoring_weights():
    """
    Get current default scoring weight configurations.
    """
    return ScoringWeightsPayload(
        skills_weight=settings.DEFAULT_SKILLS_WEIGHT,
        semantic_weight=settings.DEFAULT_SEMANTIC_WEIGHT,
        experience_weight=settings.DEFAULT_EXPERIENCE_WEIGHT,
        education_weight=settings.DEFAULT_EDUCATION_WEIGHT
    )


@router.post("/scoring-weights", response_model=ScoringWeightsPayload)
def update_scoring_weights(payload: ScoringWeightsPayload):
    """
    Persistently update global default scoring weights.
    """
    total = payload.skills_weight + payload.semantic_weight + payload.experience_weight + payload.education_weight
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scoring weights must sum to 1.0 (100%). Current sum: {round(total, 4)}"
        )

    settings.DEFAULT_SKILLS_WEIGHT = payload.skills_weight
    settings.DEFAULT_SEMANTIC_WEIGHT = payload.semantic_weight
    settings.DEFAULT_EXPERIENCE_WEIGHT = payload.experience_weight
    settings.DEFAULT_EDUCATION_WEIGHT = payload.education_weight

    return payload
