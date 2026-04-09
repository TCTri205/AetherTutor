"""create stage 2 tables - flashcards, study_sessions, notes, quizzes

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-04-09 02:00:00.000000

Migration 4: Sprint 0 - Stage 2 tables
- flashcards (với SM-2 params)
- study_sessions
- notes
- note_links (bi-directional linking)
- quizzes
- quiz_results
- quiz_answers
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'c3d4e5f6a1b2'
down_revision = 'b2c3d4e5f6a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== Flashcards =====
    op.create_table(
        'flashcards',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('front', sa.Text(), nullable=False),
        sa.Column('back', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        # SM-2 Algorithm parameters
        sa.Column('sm2_ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('sm2_interval', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sm2_repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sm2_next_review', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual'),
        # manual | quiz_wrong_answer | auto_generated
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_flashcards_user_id', 'flashcards', ['user_id'])
    op.create_index('idx_flashcards_next_review', 'flashcards', ['sm2_next_review'])
    op.create_index('idx_flashcards_user_due', 'flashcards', ['user_id', 'sm2_next_review'])
    
    # ===== Study Sessions =====
    op.create_table(
        'study_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('flashcard_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quality', sa.Integer(), nullable=False),
        # SM-2 quality rating: 0-5
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flashcard_id'], ['flashcards.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_study_sessions_user_id', 'study_sessions', ['user_id'])
    op.create_index('idx_study_sessions_flashcard_id', 'study_sessions', ['flashcard_id'])
    op.create_index('idx_study_sessions_reviewed_at', 'study_sessions', ['reviewed_at'])
    
    # ===== Notes =====
    op.create_table(
        'notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('note_type', sa.String(50), nullable=False, server_default='literature'),
        # fleeting | literature | permanent | project
        sa.Column('tags', sa.ARRAY(sa.String(100)), nullable=False, server_default='{}'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_notes_user_id', 'notes', ['user_id'])
    op.create_index('idx_notes_tags_gin', 'notes', ['tags'],
                    postgresql_using='gin')
    op.create_index('idx_notes_created_at', 'notes', ['created_at'])
    
    # ===== Note Links (Bi-directional) =====
    op.create_table(
        'note_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_note_id', UUID(as_uuid=True), nullable=False),
        sa.Column('target_note_id', UUID(as_uuid=True), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('link_type', sa.String(50), nullable=False, server_default='manual'),
        # manual | ai_suggested | confirmed
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_note_id', 'target_note_id',
                           name='uq_note_links_source_target'),
    )
    
    op.create_index('idx_note_links_user_id', 'note_links', ['user_id'])
    op.create_index('idx_note_links_source', 'note_links', ['source_note_id'])
    op.create_index('idx_note_links_target', 'note_links', ['target_note_id'])
    
    # ===== Quizzes =====
    op.create_table(
        'quizzes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('topic', sa.String(255), nullable=True),
        sa.Column('num_questions', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('question_types', sa.ARRAY(sa.String(50)), nullable=False,
                  server_default=sa.text("'{multiple_choice}'::varchar[]")),
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='3'),
        # 1-5 scale
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    )
    
    op.create_index('idx_quizzes_user_id', 'quizzes', ['user_id'])
    op.create_index('idx_quizzes_document_id', 'quizzes', ['document_id'])
    
    # ===== Quiz Results =====
    op.create_table(
        'quiz_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quiz_id', UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        # Percentage 0-100
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('correct_answers', sa.Integer(), nullable=False),
        sa.Column('weak_areas', sa.JSON(), nullable=False, server_default='[]'),
        # List of entity names user struggled with
        sa.Column('quality_rating', sa.SmallInteger(), nullable=True),
        # 1-5 rating từ user
        sa.Column('quality_feedback', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_quiz_results_user_id', 'quiz_results', ['user_id'])
    op.create_index('idx_quiz_results_quiz_id', 'quiz_results', ['quiz_id'])
    op.create_index('idx_quiz_results_completed_at', 'quiz_results', ['completed_at'])
    
    # ===== Quiz Answers =====
    op.create_table(
        'quiz_answers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quiz_result_id', UUID(as_uuid=True), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(50), nullable=False),
        # multiple_choice | true_false
        sa.Column('user_answer', sa.JSON(), nullable=False),
        sa.Column('correct_answer', sa.JSON(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('entity_name', sa.String(255), nullable=True),
        # Entity liên quan để tính weak areas
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_result_id'], ['quiz_results.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_quiz_answers_result_id', 'quiz_answers', ['quiz_result_id'])
    op.create_index('idx_quiz_answers_user_id', 'quiz_answers', ['user_id'])
    op.create_index('idx_quiz_answers_correct', 'quiz_answers', ['is_correct'])


def downgrade() -> None:
    # Drop theo thứ tự ngược lại (foreign key dependencies)
    op.drop_index('idx_quiz_answers_correct', table_name='quiz_answers')
    op.drop_index('idx_quiz_answers_user_id', table_name='quiz_answers')
    op.drop_index('idx_quiz_answers_result_id', table_name='quiz_answers')
    op.drop_table('quiz_answers')
    
    op.drop_index('idx_quiz_results_completed_at', table_name='quiz_results')
    op.drop_index('idx_quiz_results_quiz_id', table_name='quiz_results')
    op.drop_index('idx_quiz_results_user_id', table_name='quiz_results')
    op.drop_table('quiz_results')
    
    op.drop_index('idx_quizzes_document_id', table_name='quizzes')
    op.drop_index('idx_quizzes_user_id', table_name='quizzes')
    op.drop_table('quizzes')
    
    op.drop_index('idx_note_links_target', table_name='note_links')
    op.drop_index('idx_note_links_source', table_name='note_links')
    op.drop_index('idx_note_links_user_id', table_name='note_links')
    op.drop_table('note_links')
    
    op.drop_index('idx_notes_created_at', table_name='notes')
    op.drop_index('idx_notes_tags_gin', table_name='notes')
    op.drop_index('idx_notes_user_id', table_name='notes')
    op.drop_table('notes')
    
    op.drop_index('idx_study_sessions_reviewed_at', table_name='study_sessions')
    op.drop_index('idx_study_sessions_flashcard_id', table_name='study_sessions')
    op.drop_index('idx_study_sessions_user_id', table_name='study_sessions')
    op.drop_table('study_sessions')
    
    op.drop_index('idx_flashcards_user_due', table_name='flashcards')
    op.drop_index('idx_flashcards_next_review', table_name='flashcards')
    op.drop_index('idx_flashcards_user_id', table_name='flashcards')
    op.drop_table('flashcards')
