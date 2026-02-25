"""add skill_rankings table

Revision ID: 779d1e6be265
Revises: 789a10644274
Create Date: 2026-02-25 22:22:11.896149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '779d1e6be265'
down_revision: Union[str, None] = '789a10644274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('skill_rankings',
    sa.Column('department', sa.String(length=10), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('methodology', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('filters_hash', sa.String(length=64), nullable=True),
    sa.Column('ai_model_used', sa.String(length=50), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_rankings_department'), 'skill_rankings', ['department'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_skill_rankings_department'), table_name='skill_rankings')
    op.drop_table('skill_rankings')
