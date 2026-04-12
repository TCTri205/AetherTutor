"""Stage 3: Graph editing - version columns, graph_edit_log, user_id for graph_relations

Revision ID: s9a1b2c3d4e5
Revises: 94ab85f4bf75
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 's9a1b2c3d4e5'
down_revision: Union[str, None] = '94ab85f4bf75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 1. Add user_id to graph_relations  (User Isolation BR-001)
    # ---------------------------------------------------------------
    op.add_column(
        "graph_relations",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,  # nullable temporarily for backfill
        ),
    )

    # Backfill: copy user_id from the parent document
    op.execute(
        """
        UPDATE graph_relations gr
        SET user_id = d.user_id
        FROM documents d
        WHERE gr.document_id = d.id
        """
    )

    # Now make it NOT NULL
    op.alter_column(
        "graph_relations",
        "user_id",
        nullable=False,
    )

    # Index for user-scoped queries
    op.create_index(
        "idx_graph_relations_user_id",
        "graph_relations",
        ["user_id"],
    )

    # ---------------------------------------------------------------
    # 2. Add version + updated_at to graph_entities
    # ---------------------------------------------------------------
    op.add_column(
        "graph_entities",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "graph_entities",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    # ---------------------------------------------------------------
    # 3. Add version + updated_at to graph_relations
    # ---------------------------------------------------------------
    op.add_column(
        "graph_relations",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "graph_relations",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    # ---------------------------------------------------------------
    # 4. Create graph_edit_log table (audit trail)
    # ---------------------------------------------------------------
    op.create_table(
        "graph_edit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("graph_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("graph_relations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),  # CREATE, UPDATE, DELETE
        sa.Column("entity_type", sa.String(20), nullable=False),  # entity, relation
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    op.create_index("idx_graph_edit_log_user_id", "graph_edit_log", ["user_id"])
    op.create_index("idx_graph_edit_log_document_id", "graph_edit_log", ["document_id"])
    op.create_index("idx_graph_edit_log_created_at", "graph_edit_log", ["created_at"])

    # ---------------------------------------------------------------
    # 5. Performance indexes for version columns
    # ---------------------------------------------------------------
    op.create_index(
        "idx_graph_entities_version",
        "graph_entities",
        ["version"],
    )
    op.create_index(
        "idx_graph_relations_version",
        "graph_relations",
        ["version"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_graph_relations_version", table_name="graph_relations")
    op.drop_index("idx_graph_entities_version", table_name="graph_entities")
    op.drop_index("idx_graph_edit_log_created_at", table_name="graph_edit_log")
    op.drop_index("idx_graph_edit_log_document_id", table_name="graph_edit_log")
    op.drop_index("idx_graph_edit_log_user_id", table_name="graph_edit_log")

    # Drop graph_edit_log table
    op.drop_table("graph_edit_log")

    # Drop version + updated_at columns
    op.drop_column("graph_relations", "updated_at")
    op.drop_column("graph_relations", "version")
    op.drop_column("graph_entities", "updated_at")
    op.drop_column("graph_entities", "version")

    # Drop user_id from graph_relations
    op.drop_index("idx_graph_relations_user_id", table_name="graph_relations")
    op.drop_column("graph_relations", "user_id")
