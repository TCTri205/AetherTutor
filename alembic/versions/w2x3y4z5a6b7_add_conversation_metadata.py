"""Add metadata JSON field to conversations for pedagogical state tracking

Revision ID: w2x3y4z5a6b7
Revises: v1w2x3y4z5a6
Create Date: 2026-04-12

BR-006: Thêm metadata field để track attempt_count và pedagogical state trong Socratic chat.
"""
from alembic import op
import sqlalchemy as sa

revision = 'w2x3y4z5a6b7'
down_revision = 'v1w2x3y4z5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Thêm metadata JSON column vào conversations table."""
    op.add_column(
        'conversations',
        sa.Column('metadata', sa.JSON(), nullable=True, server_default='{}')
    )

    # Lưu ý: Không tạo GIN index trên JSON column vì PostgreSQL không hỗ trợ trực tiếp.
    # Nếu cần query metadata, dùng JSONB hoặc btree index trên specific keys.
    # Bỏ GIN index để tránh lỗi: "data type json has no default operator class for access method gin"

    print("✓ Added metadata JSON column to conversations")


def downgrade() -> None:
    """Xóa metadata column."""
    # Không có index để drop vì đã bỏ GIN index trong upgrade
    op.drop_column('conversations', 'metadata')

    print("✓ Removed metadata column from conversations")
