"""sprint21 graph updates

Revision ID: z1a2b3c4d5e6
Revises: v4w5x6y7z8a9
Create Date: 2026-04-14 22:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'z1a2b3c4d5e6'
down_revision = 'v4w5x6y7z8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add position columns to graph_entities
    op.add_column('graph_entities', sa.Column('position_x', sa.Float(), nullable=True))
    op.add_column('graph_entities', sa.Column('position_y', sa.Float(), nullable=True))
    op.create_index('idx_graph_entities_position', 'graph_entities', ['position_x', 'position_y'])

    # 2. Create graph_versions table
    op.create_table(
        'graph_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('graph_data', postgresql.JSONB, nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('is_auto_save', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_graph_versions_doc_id', 'graph_versions', ['document_id'])
    op.create_index('idx_graph_versions_user_id', 'graph_versions', ['user_id'])
    op.create_index('idx_graph_versions_created_at', 'graph_versions', ['created_at'])


def downgrade() -> None:
    # 1. Drop graph_versions table
    op.drop_table('graph_versions')

    # 2. Remove position columns from graph_entities
    op.drop_index('idx_graph_entities_position', table_name='graph_entities')
    op.drop_column('graph_entities', 'position_y')
    op.drop_column('graph_entities', 'position_x')
