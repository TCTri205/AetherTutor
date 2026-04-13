"""Enable Row-Level Security (RLS) on sensitive tables

Revision ID: v1w2x3y4z5a6
Revises: u2v3w4x5y6z7
Create Date: 2026-04-12

BR-001: Implement Row-Level Security để cô lập dữ liệu theo user_id ở database level.
"""
from alembic import op
import sqlalchemy as sa

revision = 'v1w2x3y4z5a6'
down_revision = 'u2v3w4x5y6z7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Enable Row-Level Security (RLS) trên các bảng nhạy cảm.
    
    RLS đảm bảo rằng mỗi user chỉ có thể truy cập dữ liệu của chính họ,
    ngay cả khi có bug ở application layer (SQLAlchemy filters).
    
    Strategy:
    - Bật RLS trên các bảng có user_id
    - Tạo policy: user chỉ được SELECT/INSERT/UPDATE/DELETE rows có user_id của họ
    - Không áp dụng cho superuser/admin roles (bypass RLS)
    """
    
    # Danh sách bảng cần bật RLS (chỉ các bảng CÓ cột user_id)
    # Lưu ý: conversations, messages KHÔNG có user_id trực tiếp (liên kết qua document_id)
    tables_with_user_id = [
        'documents',
        'flashcards',
        'study_sessions',
        'notes',
        'quizzes',
        'quiz_results',
        'quiz_answers',
        'topics',
        'graph_entities',
        'graph_relations',
        'entity_aliases',
        'graph_edit_log',
        'user_sessions',
        'note_entity_links',
        'study_session_groups',
        'note_links',
    ]
    
    for table_name in tables_with_user_id:
        # Bật RLS trên bảng
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        
        # Tạo policy cho SELECT
        op.execute(f"""
            CREATE POLICY {table_name}_user_isolation ON {table_name}
            FOR ALL
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """)
        
        print(f"✓ Enabled RLS on {table_name}")
    
    # Tạo function để set current_user_id tự động
    op.execute("""
        CREATE OR REPLACE FUNCTION set_current_user_id()
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_user_id', current_setting('app.current_user_id', true), true);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    print("✓ Row-Level Security enabled on all sensitive tables")


def downgrade() -> None:
    """Tắt RLS trên tất cả các bảng."""

    tables_with_user_id = [
        'documents',
        'flashcards',
        'study_sessions',
        'notes',
        'quizzes',
        'quiz_results',
        'quiz_answers',
        'topics',
        'graph_entities',
        'graph_relations',
        'entity_aliases',
        'graph_edit_log',
        'user_sessions',
        'note_entity_links',
        'study_session_groups',
        'note_links',
    ]
    
    for table_name in tables_with_user_id:
        # Xóa policy
        op.execute(f"DROP POLICY IF EXISTS {table_name}_user_isolation ON {table_name}")
        
        # Tắt RLS
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")
        
        print(f"✓ Disabled RLS on {table_name}")
    
    # Xóa function
    op.execute("DROP FUNCTION IF EXISTS set_current_user_id()")
    
    print("✓ Row-Level Security disabled")
