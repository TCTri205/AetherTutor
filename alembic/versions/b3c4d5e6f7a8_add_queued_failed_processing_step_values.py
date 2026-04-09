"""add_queued_failed_processing_step_values

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-10

Adds missing QUEUED and FAILED values to the processingstep enum.
Also fixes entity_aliases.confidence server_default from 0.0 to 1.0.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing enum values to processingstep
    op.execute("ALTER TYPE processingstep ADD VALUE IF NOT EXISTS 'QUEUED'")
    op.execute("ALTER TYPE processingstep ADD VALUE IF NOT EXISTS 'FAILED'")

    # Fix entity_aliases.confidence server_default
    op.alter_column(
        'entity_aliases',
        'confidence',
        server_default='1.0'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values without recreating the type.
    # This downgrade is intentionally a no-op for the enum values.
    # To fully downgrade, you would need to:
    # 1. Create a new enum without QUEUED/FAILED
    # 2. Update all rows using those values
    # 3. Drop the old enum and rename the new one
    pass
