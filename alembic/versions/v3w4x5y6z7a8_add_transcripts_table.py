"""Add transcripts table for Sprint 17 - Media Microlearning

Revision ID: v3w4x5y6z7a8
Revises: x3y4z5a6b7c8
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'v3w4x5y6z7a8'
down_revision: Union[str, None] = '5ac04741e04b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_text', sa.Text, nullable=False, server_default=''),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('duration', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('segments', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )

    # Indexes for performance and unique constraint
    op.create_index('idx_transcripts_user_id', 'transcripts', ['user_id'])
    op.create_index('idx_transcripts_document_id', 'transcripts', ['document_id'])
    op.create_index('idx_transcripts_status', 'transcripts', ['status'])
    op.create_unique_constraint('uq_transcripts_document', 'transcripts', ['document_id'])


def downgrade() -> None:
    op.drop_index('idx_transcripts_status')
    op.drop_index('idx_transcripts_document_id')
    op.drop_index('idx_transcripts_user_id')
    op.drop_constraint('uq_transcripts_document', 'transcripts')
    op.drop_table('transcripts')
