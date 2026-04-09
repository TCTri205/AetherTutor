"""add user_id to graph_entities and create entity_aliases table

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-09 01:00:00.000000

Migration 2 & 3: Sprint 0 - Graph multi-tenant + entity alias resolution
- Thêm user_id vào graph_entities
- Tạo bảng entity_aliases cho cross-document entity resolution
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    # ===== Migration 2: Thêm user_id vào graph_entities =====
    
    # Bước 1: Thêm cột user_id
    op.add_column(
        'graph_entities',
        sa.Column('user_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Bước 2: Gán default user cho entities hiện tại
    # (JOIN với documents để lấy user_id đúng)
    op.execute(
        sa.text("""
            UPDATE graph_entities ge
            SET user_id = d.user_id
            FROM documents d
            WHERE ge.document_id = d.id
              AND ge.user_id IS NULL
        """)
    )
    
    # Bước 3: Đặt NOT NULL
    op.alter_column(
        'graph_entities',
        'user_id',
        nullable=False,
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
    )
    
    # Bước 4: Foreign key và indexes
    op.create_foreign_key(
        'fk_graph_entities_user_id',
        'graph_entities', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_index('idx_graph_entities_user_id', 'graph_entities', ['user_id'])
    
    # ===== Migration 3: Tạo bảng entity_aliases =====
    
    op.create_table(
        'entity_aliases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('alias_name', sa.String(255), nullable=False),
        sa.Column('canonical_name', sa.String(255), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'alias_name', name='uq_entity_aliases_user_alias'),
    )
    
    # Indexes
    op.create_index('idx_entity_aliases_canonical', 'entity_aliases', ['canonical_name'])
    op.create_index('idx_entity_aliases_alias', 'entity_aliases', ['alias_name'])
    op.create_index('idx_entity_aliases_user_id', 'entity_aliases', ['user_id'])


def downgrade() -> None:
    # Xóa entity_aliases
    op.drop_index('idx_entity_aliases_user_id', table_name='entity_aliases')
    op.drop_index('idx_entity_aliases_alias', table_name='entity_aliases')
    op.drop_index('idx_entity_aliases_canonical', table_name='entity_aliases')
    op.drop_table('entity_aliases')
    
    # Xóa user_id khỏi graph_entities
    op.drop_constraint('fk_graph_entities_user_id', 'graph_entities', type_='foreignkey')
    op.drop_index('idx_graph_entities_user_id', table_name='graph_entities')
    op.drop_column('graph_entities', 'user_id')
