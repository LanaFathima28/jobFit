"""Add ingestion metadata to Candidate and Job tables

Revision ID: 002_add_ingestion_metadata
Revises: 001_initial_schema
Create Date: 2026-09-19 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_ingestion_metadata'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to candidates
    op.add_column('candidates', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('candidates', sa.Column('file_type', sa.String(length=50), nullable=True))
    op.add_column('candidates', sa.Column('file_path', sa.String(length=512), nullable=True))
    op.add_column('candidates', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('candidates', sa.Column('extraction_status', sa.String(length=50), nullable=True, server_default='pending'))
    op.add_column('candidates', sa.Column('extraction_error', sa.Text(), nullable=True))

    # Add columns to jobs
    op.add_column('jobs', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('jobs', sa.Column('file_type', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('file_path', sa.String(length=512), nullable=True))
    op.add_column('jobs', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('extraction_status', sa.String(length=50), nullable=True, server_default='pending'))
    op.add_column('jobs', sa.Column('extraction_error', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from jobs
    op.drop_column('jobs', 'extraction_error')
    op.drop_column('jobs', 'extraction_status')
    op.drop_column('jobs', 'file_size')
    op.drop_column('jobs', 'file_path')
    op.drop_column('jobs', 'file_type')
    op.drop_column('jobs', 'original_filename')

    # Remove columns from candidates
    op.drop_column('candidates', 'extraction_error')
    op.drop_column('candidates', 'extraction_status')
    op.drop_column('candidates', 'file_size')
    op.drop_column('candidates', 'file_path')
    op.drop_column('candidates', 'file_type')
    op.drop_column('candidates', 'original_filename')
