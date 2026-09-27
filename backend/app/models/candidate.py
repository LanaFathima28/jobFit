import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, Text, DateTime, JSON, UUID, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class VectorType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(1536))
        return dialect.type_descriptor(JSON())


class Candidate(Base):
    """
    Candidate model representing applicant profiles and resume data.
    """
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    
    # Vector embedding (1536 dims for text-embedding-3-small)
    embedding: Mapped[Optional[list[float]]] = mapped_column(VectorType, nullable=True)
    embedding_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ingestion Metadata
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extraction_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="pending")
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Phase 2 Structured Extraction Metadata
    structured_extraction_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="pending")
    debug_raw_llm_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    matches = relationship("Match", back_populates="candidate", cascade="all, delete-orphan")
