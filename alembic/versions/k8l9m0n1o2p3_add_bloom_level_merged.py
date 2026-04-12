"""Add bloom_level to quiz_answers (merged into main chain)

Revision ID: k8l9m0n1o2p3
Revises: t1a2b3c4d5e6
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'k8l9m0n1o2p3'
down_revision: Union[str, None] = 't1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bloom_level to quiz_answers with IF NOT EXISTS
    op.execute(
        "ALTER TABLE quiz_answers ADD COLUMN IF NOT EXISTS bloom_level VARCHAR(50)"
    )


def downgrade() -> None:
    op.drop_column("quiz_answers", "bloom_level")
