"""Merge: stage4 code_media + note_entity_links

Combines two parallel migration branches:
- p4q5r6s7t8u9: Add code_snippet to graph_entities, media_type to documents
- u2v3w4x5y6z7: Add note_entity_links table for BR-009 note backlinks

Revision ID: merge_stage4_heads
Revises: p4q5r6s7t8u9, u2v3w4x5y6z7
Create Date: 2026-04-12
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'merge_stage4_heads'
down_revision: Union[tuple[str, ...], None] = ('p4q5r6s7t8u9', 'u2v3w4x5y6z7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op merge — both parent migrations already contain all schema changes.
    
    This merge revision simply unifies the two parallel heads into a single chain:
    - p4q5r6s7t8u9 added: code_snippet, file_size (graph_entities), media_type, source_url (documents)
    - u2v3w4x5y6z7 added: note_entity_links table
    
    No additional schema changes needed here.
    """
    pass


def downgrade() -> None:
    """No-op downgrade — parent migrations handle their own downgrades."""
    pass
