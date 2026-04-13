"""Stage 4: Add code_snippet to graph_entities, media_type to documents

Revision ID: p4q5r6s7t8u9
Revises: k8l9m0n1o2p3
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'p4q5r6s7t8u9'
down_revision: Union[str, None] = 'k8l9m0n1o2p3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add code_snippet and file_size to graph_entities
    op.execute(
        "ALTER TABLE graph_entities ADD COLUMN IF NOT EXISTS code_snippet TEXT"
    )
    op.execute(
        "ALTER TABLE graph_entities ADD COLUMN IF NOT EXISTS file_size INTEGER"
    )
    # Add display_name to graph_entities (required by GraphEntity model)
    op.execute(
        "ALTER TABLE graph_entities ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)"
    )

    # Create media_type enum for documents (Sprint 17: Media Microlearning)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mediatype AS ENUM ('text', 'video', 'audio');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add media_type and source_url to documents
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS media_type mediatype DEFAULT 'text'"
    )
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url VARCHAR(1024)"
    )


def downgrade() -> None:
    op.drop_column("documents", "source_url")
    op.drop_column("documents", "media_type")
    op.execute("DROP TYPE IF EXISTS mediatype")
    op.drop_column("graph_entities", "display_name")
    op.drop_column("graph_entities", "file_size")
    op.drop_column("graph_entities", "code_snippet")
