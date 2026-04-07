"""add processing_step enum to documents

Revision ID: f9866332f658
Revises: 5f4b730b3577
Create Date: 2026-04-07 15:48:44.653482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9866332f658'
down_revision: Union[str, Sequence[str], None] = '5f4b730b3577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the Enum type first
    processing_step_enum = sa.Enum('INITIAL', 'EXTRACTING', 'CHUNKING', 'EXTRACTING_ENTITIES', 'BUILDING_GRAPH', 'EMBEDDING', 'COMPLETED', name='processingstep')
    processing_step_enum.create(op.get_bind(), checkfirst=True)

    # Add column as nullable first
    op.add_column('documents', sa.Column('processing_step', processing_step_enum, nullable=True))
    
    # Update existing docs: if status is COMPLETED, set step to COMPLETED, else INITIAL
    op.execute("UPDATE documents SET processing_step = 'COMPLETED' WHERE status = 'COMPLETED'")
    op.execute("UPDATE documents SET processing_step = 'INITIAL' WHERE status != 'COMPLETED'")
    
    # Set to NOT NULL
    op.alter_column('documents', 'processing_step', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'processing_step')
    sa.Enum(name='processingstep').drop(op.get_bind(), checkfirst=True)
