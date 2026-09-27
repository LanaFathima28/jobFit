"""Add structured_extraction_status and debug_raw_llm_output columns to Candidate and Job tables

Revision ID: 003_add_structured_extraction_metadata
Revises: 002_add_ingestion_metadata
Create Date: 2026-09-19 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002_add_ingestion_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to candidates
    op.add_column('candidates', sa.Column('structured_extraction_status', sa.String(length=50), nullable=True, server_default='pending'))
    op.add_column('candidates', sa.Column('debug_raw_llm_output', sa.Text(), nullable=True))

    # Add columns to jobs
    op.add_column('jobs', sa.Column('structured_extraction_status', sa.String(length=50), nullable=True, server_default='pending'))
    op.add_column('jobs', sa.Column('debug_raw_llm_output', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from jobs
    op.drop_column('jobs', 'debug_raw_llm_output')
    op.drop_column('jobs', 'structured_extraction_status')

    # Remove columns from candidates
    op.drop_column('candidates', 'debug_raw_llm_output')
    op.drop_column('candidates', 'structured_extraction_status')
