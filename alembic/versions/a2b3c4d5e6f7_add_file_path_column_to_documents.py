"""add_file_path_column_to_documents

Revision ID: a2b3c4d5e6f7
Revises: f1cbb2b51663
Create Date: 2026-04-10

Adds the missing `file_path` column to the `documents` table.
This column exists in the SQLAlchemy model but was never migrated.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1cbb2b51663'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'documents',
        sa.Column('file_path', sa.String(512), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'file_path')
