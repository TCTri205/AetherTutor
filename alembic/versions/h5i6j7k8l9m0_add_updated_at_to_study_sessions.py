"""add updated_at column to study_sessions

Revision ID: h5i6j7k8l9m0
Revises: b3c4d5e6f7a8
Create Date: 2026-04-10 11:00:00.000000

Fix: StudySession model inherits TimestampMixin but database column was
never created in migration c3d4e5f6a1b2.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h5i6j7k8l9m0'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at to study_sessions table."""
    op.execute(
        "ALTER TABLE study_sessions "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE "
        "NOT NULL DEFAULT NOW()"
    )


def downgrade() -> None:
    """Remove updated_at from study_sessions table."""
    op.execute(
        "ALTER TABLE study_sessions DROP COLUMN IF EXISTS updated_at"
    )
