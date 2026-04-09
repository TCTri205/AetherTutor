"""convert graph_relations from String to UUID FK

Revision ID: d4e5f6a1b2c3
Revises: c3d4e5f6a1b2
Create Date: 2026-04-09 03:00:00.000000

Migration 5: Sprint 0 - Breaking Change
CHÚ Ý: Đây là migration phức tạp và rủi ro nhất Stage 2.
Chuyển source_entity/target_entity từ String(255) sang UUID FK -> graph_entities.id

PREREQUISITES:
1. Chạy script clean_entity_names.py TRƯỚC để resolve >= 95% entity names
2. Backup DB: pg_dump aethertutor > backup_pre_migration5.sql
3. Chạy trên staging trước khi apply production

ROLLBACK PLAN:
- Giữ script đảo ngược trong scripts/rollback_migration5.py
- Restore source_entity/target_entity từ canonical_name lookup
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'd4e5f6a1b2c3'
down_revision = 'c3d4e5f6a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bước 1: Thêm cột mới tạm thời (nullable)
    op.add_column(
        'graph_relations',
        sa.Column('source_entity_id', UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'graph_relations',
        sa.Column('target_entity_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Bước 2: Populate UUIDs từ canonical_name lookup
    # UPDATE source_entity_id
    op.execute(
        sa.text("""
            UPDATE graph_relations gr
            SET source_entity_id = ge.id
            FROM graph_entities ge
            WHERE gr.source_entity = ge.canonical_name
              AND gr.document_id = ge.document_id
        """)
    )
    
    # UPDATE target_entity_id
    op.execute(
        sa.text("""
            UPDATE graph_relations gr
            SET target_entity_id = ge.id
            FROM graph_entities ge
            WHERE gr.target_entity = ge.canonical_name
              AND gr.document_id = ge.document_id
        """)
    )
    
    # Bước 3: Kiểm tra xem có rows nào không resolve được không
    # (Nên đã chạy clean_entity_names.py trước)
    # Nếu có unresolved, migration sẽ vẫn chạy nhưng các rows đó sẽ có NULL
    
    # Bước 4: Đặt NOT NULL constraints
    op.alter_column(
        'graph_relations',
        'source_entity_id',
        nullable=False,
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
    )
    op.alter_column(
        'graph_relations',
        'target_entity_id',
        nullable=False,
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
    )
    
    # Bước 5: Tạo foreign keys
    op.create_foreign_key(
        'fk_graph_relations_source_entity',
        'graph_relations', 'graph_entities',
        ['source_entity_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_graph_relations_target_entity',
        'graph_relations', 'graph_entities',
        ['target_entity_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Bước 6: Tạo indexes cho FK columns
    op.create_index(
        'idx_graph_relations_source_id',
        'graph_relations',
        ['source_entity_id']
    )
    op.create_index(
        'idx_graph_relations_target_id',
        'graph_relations',
        ['target_entity_id']
    )
    
    # Bước 7: Xóa columns cũ String
    op.drop_constraint(
        'uq_document_relation',
        'graph_relations',
        type_='unique'
    )
    op.execute("DROP INDEX IF EXISTS idx_graph_relations_source_entity")
    op.execute("DROP INDEX IF EXISTS idx_graph_relations_target_entity")
    op.execute("DROP INDEX IF EXISTS idx_graph_relations_source")
    op.execute("DROP INDEX IF EXISTS idx_graph_relations_target")
    op.execute("DROP INDEX IF EXISTS ix_graph_relations_source_entity")
    op.execute("DROP INDEX IF EXISTS ix_graph_relations_target_entity")
    op.drop_column('graph_relations', 'source_entity')
    op.drop_column('graph_relations', 'target_entity')
    
    # Bước 8: Tạo lại unique constraint với UUIDs
    op.create_unique_constraint(
        'uq_graph_relations_doc_source_target_type',
        'graph_relations',
        ['document_id', 'source_entity_id', 'target_entity_id', 'relation_type']
    )


def downgrade() -> None:
    # Bước 1: Thêm lại columns cũ String
    op.add_column(
        'graph_relations',
        sa.Column('source_entity', sa.String(255), nullable=True)
    )
    op.add_column(
        'graph_relations',
        sa.Column('target_entity', sa.String(255), nullable=True)
    )
    
    # Bước 2: Populate lại từ canonical_name lookup
    op.execute(
        sa.text("""
            UPDATE graph_relations gr
            SET source_entity = ge.canonical_name
            FROM graph_entities ge
            WHERE gr.source_entity_id = ge.id
        """)
    )
    op.execute(
        sa.text("""
            UPDATE graph_relations gr
            SET target_entity = ge.canonical_name
            FROM graph_entities ge
            WHERE gr.target_entity_id = ge.id
        """)
    )
    
    # Bước 3: Đặt NOT NULL
    op.alter_column(
        'graph_relations',
        'source_entity',
        nullable=False,
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        'graph_relations',
        'target_entity',
        nullable=False,
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    
    # Bước 4: Xóa FKs và indexes mới
    op.drop_constraint('uq_graph_relations_doc_source_target_type', 'graph_relations', type_='unique')
    op.drop_index('idx_graph_relations_target_id', table_name='graph_relations')
    op.drop_index('idx_graph_relations_source_id', table_name='graph_relations')
    op.drop_constraint('fk_graph_relations_target_entity', 'graph_relations', type_='foreignkey')
    op.drop_constraint('fk_graph_relations_source_entity', 'graph_relations', type_='foreignkey')
    
    # Bước 5: Xóa columns UUID
    op.drop_column('graph_relations', 'source_entity_id')
    op.drop_column('graph_relations', 'target_entity_id')
    
    # Bước 6: Tạo lại indexes và constraints cũ
    op.create_index('idx_graph_relations_target_entity', 'graph_relations', ['target_entity'])
    op.create_index('idx_graph_relations_source_entity', 'graph_relations', ['source_entity'])
    op.create_unique_constraint(
        'uq_document_relation',
        'graph_relations',
        ['document_id', 'source_entity', 'target_entity', 'relation_type']
    )
