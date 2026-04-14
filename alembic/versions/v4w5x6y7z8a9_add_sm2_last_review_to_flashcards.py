"""add sm2_last_review to flashcards

Revision ID: v4w5x6y7z8a9
Revises: idx_fk_perf_20260414
Create Date: 2026-04-14 22:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v4w5x6y7z8a9'
down_revision = 'idx_fk_perf_20260414'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sm2_last_review column to flashcards
    op.add_column('flashcards', sa.Column('sm2_last_review', sa.DateTime(), nullable=True, comment='Timestamp of the last review (for tracking & analytics)'))


def downgrade() -> None:
    # Remove sm2_last_review column from flashcards
    op.drop_column('flashcards', 'sm2_last_review')
