"""Add embedding_input columns and HNSW vector indices to Candidate and Job tables

Revision ID: 004_add_embedding_input_and_vector_indices
Revises: 003_add_structured_extraction_metadata
Create Date: 2026-09-19 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add embedding_input column to candidates and jobs
    op.add_column('candidates', sa.Column('embedding_input', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('embedding_input', sa.Text(), nullable=True))

    # Create HNSW Vector Index on PostgreSQL for cosine similarity
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS idx_candidates_embedding_hnsw ON candidates USING hnsw (embedding vector_cosine_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw ON jobs USING hnsw (embedding vector_cosine_ops);")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw;")
        op.execute("DROP INDEX IF EXISTS idx_candidates_embedding_hnsw;")

    op.drop_column('jobs', 'embedding_input')
    op.drop_column('candidates', 'embedding_input')
