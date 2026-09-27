"""Add sub-scores and score_breakdown JSON to matches table

Revision ID: 005_add_hybrid_scoring_breakdown_to_matches
Revises: 004_add_embedding_input_and_vector_indices
Create Date: 2026-09-19 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('matches', sa.Column('skill_overlap_score', sa.Float(), nullable=True))
    op.add_column('matches', sa.Column('experience_score', sa.Float(), nullable=True))
    op.add_column('matches', sa.Column('education_score', sa.Float(), nullable=True))
    op.add_column('matches', sa.Column('score_breakdown', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True))


def downgrade() -> None:
    op.drop_column('matches', 'score_breakdown')
    op.drop_column('matches', 'education_score')
    op.drop_column('matches', 'experience_score')
    op.drop_column('matches', 'skill_overlap_score')
