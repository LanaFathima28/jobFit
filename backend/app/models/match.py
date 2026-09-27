import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Float, Text, DateTime, JSON, ForeignKey, UUID, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Match(Base):
    """
    Match model linking Candidates to Jobs with hybrid scoring & LLM explanations.
    """
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    
    semantic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rule_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skill_overlap_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    education_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    score_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interview_questions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    candidate = relationship("Candidate", back_populates="matches")
    job = relationship("Job", back_populates="matches")
