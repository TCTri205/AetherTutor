"""add missing flashcard columns and indexes

Revision ID: g4h5i6j7k8l9
Revises: c3d4e5f6a1b2
Create Date: 2026-04-10 05:00:00.000000

Bug Fix Migration:
- Add document_id column to flashcards table
- Add idempotency_key column to study_sessions table
- Add missing idx_flashcards_user_source index
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'g4h5i6j7k8l9'
down_revision = 'c3d4e5f6a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== Flashcards: Add document_id =====
    op.add_column(
        'flashcards',
        sa.Column('document_id', UUID(as_uuid=True), nullable=True)
    )

    op.create_foreign_key(
        'fk_flashcards_document_id',
        'flashcards', 'documents',
        ['document_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_index(
        'idx_flashcards_document_id',
        'flashcards',
        ['document_id']
    )

    # ===== Flashcards: Add missing user_source index =====
    op.create_index(
        'idx_flashcards_user_source',
        'flashcards',
        ['user_id', 'source']
    )

    # ===== Study Sessions: Add idempotency_key =====
    op.add_column(
        'study_sessions',
        sa.Column('idempotency_key', sa.String(100), nullable=True)
    )

    op.create_index(
        'idx_study_sessions_idempotency_key',
        'study_sessions',
        ['idempotency_key']
    )


def downgrade() -> None:
    # Drop study_sessions idempotency_key
    op.drop_index('idx_study_sessions_idempotency_key', table_name='study_sessions')
    op.drop_column('study_sessions', 'idempotency_key')

    # Drop flashcards user_source index
    op.drop_index('idx_flashcards_user_source', table_name='flashcards')

    # Drop flashcards document_id
    op.drop_index('idx_flashcards_document_id', table_name='flashcards')
    op.drop_constraint('fk_flashcards_document_id', 'flashcards', type_='foreignkey')
    op.drop_column('flashcards', 'document_id')
