"""fix_entity_aliases_schema

Revision ID: c813c3f20a5b
Revises: e5f6a1b2c3d4
Create Date: 2026-04-10 00:39:59.415204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c813c3f20a5b'
down_revision: Union[str, Sequence[str], None] = 'e5f6a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename/adjust entity_aliases columns to match model
    op.drop_column('entity_aliases', 'is_confirmed')
    op.add_column('entity_aliases', sa.Column('source', sa.String(length=50), server_default='manual', nullable=False))


def downgrade() -> None:
    op.drop_column('entity_aliases', 'source')
    op.add_column('entity_aliases', sa.Column('is_confirmed', sa.Boolean(), server_default='false', nullable=False))
