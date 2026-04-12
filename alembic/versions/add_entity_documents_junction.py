"""Add entity_documents junction table for entity-document many-to-many

Revision ID: add_entity_documents
Revises: merge_stage4_heads
Create Date: 2026-04-12

Creates junction table for many-to-many relationship between 
graph_entities and documents, supporting cross-document entity resolution.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_entity_documents'
down_revision: Union[str, None] = 'merge_stage4_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entity_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('graph_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )

    # Indexes for query performance
    op.create_index('idx_entity_documents_entity_id', 'entity_documents', ['entity_id'])
    op.create_index('idx_entity_documents_document_id', 'entity_documents', ['document_id'])

    # Unique constraint: prevent duplicate entity-document links
    op.create_unique_constraint(
        'uq_entity_documents_entity_document',
        'entity_documents',
        ['entity_id', 'document_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_entity_documents_entity_document', 'entity_documents', type_='unique')
    op.drop_index('idx_entity_documents_document_id', table_name='entity_documents')
    op.drop_index('idx_entity_documents_entity_id', table_name='entity_documents')
    op.drop_table('entity_documents')
