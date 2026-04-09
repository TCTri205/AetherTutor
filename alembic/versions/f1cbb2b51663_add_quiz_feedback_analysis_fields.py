"""add_quiz_feedback_analysis_fields

Revision ID: f1cbb2b51663
Revises: c813c3f20a5b
Create Date: 2026-04-10 03:07:40.929034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1cbb2b51663'
down_revision: Union[str, Sequence[str], None] = 'c813c3f20a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('quiz_results', sa.Column('feedback_category', sa.String(50), nullable=True))
    op.add_column('quiz_results', sa.Column('feedback_severity', sa.String(20), nullable=True))
    op.add_column('quiz_results', sa.Column('feedback_suggestion', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quiz_results', 'feedback_suggestion')
    op.drop_column('quiz_results', 'feedback_severity')
    op.drop_column('quiz_results', 'feedback_category')
