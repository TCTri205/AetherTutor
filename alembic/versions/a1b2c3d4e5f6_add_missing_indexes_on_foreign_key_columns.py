"""add missing indexes on foreign key columns

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing indexes on foreign key columns for query performance."""
    
    # idx_conversations_document_id
    op.create_index(
        'idx_conversations_document_id',
        'conversations',
        ['document_id'],
        unique=False
    )
    
    # idx_messages_conversation_id
    op.create_index(
        'idx_messages_conversation_id',
        'messages',
        ['conversation_id'],
        unique=False
    )
    
    # idx_documents_user_id
    op.create_index(
        'idx_documents_user_id',
        'documents',
        ['user_id'],
        unique=False
    )
    
    # idx_graph_relations_document_id
    op.create_index(
        'idx_graph_relations_document_id',
        'graph_relations',
        ['document_id'],
        unique=False
    )
    
    # idx_graph_entities_document_id
    op.create_index(
        'idx_graph_entities_document_id',
        'graph_entities',
        ['document_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove indexes added in upgrade."""
    op.drop_index('idx_graph_entities_document_id', table_name='graph_entities')
    op.drop_index('idx_graph_relations_document_id', table_name='graph_relations')
    op.drop_index('idx_documents_user_id', table_name='documents')
    op.drop_index('idx_messages_conversation_id', table_name='messages')
    op.drop_index('idx_conversations_document_id', table_name='conversations')
