"""merge audit fixes heads

Revision ID: x3y4z5a6b7c8
Revises: 26dc0adc05ed, w2x3y4z5a6b7
Create Date: 2026-04-12

Merge hai branch:
- 26dc0adc05ed: add_graph_relations_confidence_and_metadata
- w2x3y4z5a6b7: add_conversation_metadata (audit fix P0-3)
"""
from alembic import op
import sqlalchemy as sa

revision = 'x3y4z5a6b7c8'
down_revision = ('26dc0adc05ed', 'w2x3y4z5a6b7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
