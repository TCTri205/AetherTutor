"""add performance indexes for stage 2

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-04-09 04:00:00.000000

Migration 6: Sprint 0 - Performance indexes
Thêm indexes cho các query patterns thường dùng trong Stage 2.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a1b2c3d4'
down_revision = 'd4e5f6a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Graph relations indexes (sau khi đã chuyển sang UUID FK)
    op.create_index(
        'idx_graph_relations_document_id',
        'graph_relations',
        ['document_id']
    )
    op.create_index(
        'idx_graph_relations_type',
        'graph_relations',
        ['relation_type']
    )
    
    # Graph entities indexes
    op.create_index(
        'idx_graph_entities_document_id',
        'graph_entities',
        ['document_id']
    )
    op.create_index(
        'idx_graph_entities_canonical_name',
        'graph_entities',
        ['canonical_name']
    )
    op.create_index(
        'idx_graph_entities_type',
        'graph_entities',
        ['entity_type']
    )
    
    # Document chunks indexes
    op.create_index(
        'idx_document_chunks_document_id',
        'document_chunks',
        ['document_id']
    )
    op.create_index(
        'idx_document_chunks_chunk_index',
        'document_chunks',
        ['document_id', 'chunk_index']
    )
    
    # Quiz results performance indexes
    op.create_index(
        'idx_quiz_results_user_completed',
        'quiz_results',
        ['user_id', 'completed_at']
    )
    
    # Flashcard composite indexes
    op.create_index(
        'idx_flashcards_user_source',
        'flashcards',
        ['user_id', 'source']
    )
    
    # Notes composite indexes
    op.create_index(
        'idx_notes_user_created',
        'notes',
        ['user_id', 'created_at']
    )
    
    # Conversations indexes
    op.create_index(
        'idx_conversations_user_id',
        'conversations',
        ['document_id']
    )
    op.create_index(
        'idx_messages_conversation_id',
        'messages',
        ['conversation_id']
    )


def downgrade() -> None:
    op.drop_index('idx_messages_conversation_id', table_name='messages')
    op.drop_index('idx_conversations_user_id', table_name='conversations')
    op.drop_index('idx_notes_user_created', table_name='notes')
    op.drop_index('idx_flashcards_user_source', table_name='flashcards')
    op.drop_index('idx_quiz_results_user_completed', table_name='quiz_results')
    op.drop_index('idx_document_chunks_chunk_index', table_name='document_chunks')
    op.drop_index('idx_document_chunks_document_id', table_name='document_chunks')
    op.drop_index('idx_graph_entities_type', table_name='graph_entities')
    op.drop_index('idx_graph_entities_canonical_name', table_name='graph_entities')
    op.drop_index('idx_graph_entities_document_id', table_name='graph_entities')
    op.drop_index('idx_graph_relations_type', table_name='graph_relations')
    op.drop_index('idx_graph_relations_document_id', table_name='graph_relations')
