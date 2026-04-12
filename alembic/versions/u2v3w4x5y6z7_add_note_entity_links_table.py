"""Add note_entity_links table for BR-009 note backlinks

Revision ID: u2v3w4x5y6z7
Revises: t1a2b3c4d5e6
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'u2v3w4x5y6z7'
down_revision: Union[str, None] = 't1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'note_entity_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('notes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('graph_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_type', sa.String(50), nullable=False, server_default='exact'),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )

    # Indexes for BR-001 user isolation and query performance
    op.create_index('idx_note_entity_links_user_id', 'note_entity_links', ['user_id'])
    op.create_index('idx_note_entity_links_note_id', 'note_entity_links', ['note_id'])
    op.create_index('idx_note_entity_links_entity_id', 'note_entity_links', ['entity_id'])

    # Unique constraint: one link per note-entity pair
    op.create_unique_constraint(
        'uq_note_entity_links_note_entity',
        'note_entity_links',
        ['note_id', 'entity_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_note_entity_links_note_entity', 'note_entity_links', type_='unique')
    op.drop_index('idx_note_entity_links_entity_id', table_name='note_entity_links')
    op.drop_index('idx_note_entity_links_note_id', table_name='note_entity_links')
    op.drop_index('idx_note_entity_links_user_id', table_name='note_entity_links')
    op.drop_table('note_entity_links')
