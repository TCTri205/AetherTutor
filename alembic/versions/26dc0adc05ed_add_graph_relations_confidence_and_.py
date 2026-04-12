"""add_graph_relations_confidence_and_metadata

Revision ID: 26dc0adc05ed
Revises: add_entity_documents
Create Date: 2026-04-12 19:52:01.048259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26dc0adc05ed'
down_revision: Union[str, Sequence[str], None] = 'add_entity_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing confidence and evidence columns
    op.add_column('graph_relations', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('graph_relations', sa.Column('evidence', sa.Text(), nullable=True))
    
    # Add confidence check constraint
    op.create_check_constraint(
        'ck_graph_relations_confidence_range',
        'graph_relations',
        'confidence IS NULL OR (confidence >= 0 AND confidence <= 1)'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraint and columns
    op.drop_constraint('ck_graph_relations_confidence_range', 'graph_relations', type_='check')
    op.drop_column('graph_relations', 'evidence')
    op.drop_column('graph_relations', 'confidence')
