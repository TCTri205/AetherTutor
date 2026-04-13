"""add media_type and source_url to documents

Sprint 17: Media Microlearning — Support YouTube videos and audio files.

Revision ID: 14a2cbfca0b2
Revises: 5ac04741e04b
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '14a2cbfca0b2'
down_revision: Union[str, None] = '5ac04741e04b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create media_type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mediatype AS ENUM ('text', 'video', 'audio');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add columns
    op.add_column('documents', sa.Column('media_type', sa.Enum('text', 'video', 'audio', name='mediatype'), nullable=False, server_default='text'))
    op.add_column('documents', sa.Column('source_url', sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'source_url')
    op.drop_column('documents', 'media_type')
    op.execute("DROP TYPE IF EXISTS mediatype")
