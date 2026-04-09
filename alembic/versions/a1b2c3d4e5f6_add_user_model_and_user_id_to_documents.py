"""add user model and user_id to documents

Revision ID: a1b2c3d4e5f6
Revises: f9866332f658
Create Date: 2026-04-09 00:00:00.000000

Migration 1: Sprint 0 - Multi-tenant foundation
- Tạo bảng users
- Thêm cột user_id vào bảng documents
- Tạo default user và gán cho tất cả documents hiện tại
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a1b2c3d4e5f6'
down_revision = 'f9866332f658'
branch_labels = None
depends_on = None

# Default user UUID để dễ quản lý
DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    # Bước 1: Tạo extension uuid-ossp (nếu chưa có)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Bước 2: Tạo bảng users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('preferences', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    
    # Index cho email
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Bước 3: Tạo default user
    op.execute(
        sa.text("""
            INSERT INTO users (id, email, hashed_password, is_active, is_superuser, preferences)
            VALUES (
                CAST(:default_user_id AS UUID),
                'default@aethertutor.local',
                '',
                true,
                true,
                '{}'
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(default_user_id=DEFAULT_USER_ID)
    )
    
    # Bước 4: Thêm cột user_id vào documents
    op.add_column(
        'documents',
        sa.Column('user_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Bước 5: Gán default user cho tất cả documents hiện tại
    op.execute(
        sa.text("""
            UPDATE documents
            SET user_id = CAST(:default_user_id AS UUID)
            WHERE user_id IS NULL
        """).bindparams(default_user_id=DEFAULT_USER_ID)
    )
    
    # Bước 6: Đặt NOT NULL constraint và foreign key
    op.alter_column(
        'documents',
        'user_id',
        nullable=False,
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
    )
    
    op.create_foreign_key(
        'fk_documents_user_id',
        'documents', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Index cho user_id
    op.create_index('idx_documents_user_id', 'documents', ['user_id'])


def downgrade() -> None:
    # Xóa foreign key và column
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')
    op.drop_index('idx_documents_user_id', table_name='documents')
    op.drop_column('documents', 'user_id')
    
    # Xóa default user
    op.execute(
        sa.text("DELETE FROM users WHERE id = CAST(:id AS UUID)").bindparams(id=DEFAULT_USER_ID)
    )
    
    # Xóa bảng users
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
