"""Stage 4 Phase 3: Add teams, team_members, shared_resources tables

Revision ID: t1a2b3c4d5e6
Revises: s9a1b2c3d4e5
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 't1a2b3c4d5e6'
down_revision: Union[str, None] = 's9a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create team_role_enum enum type
    op.execute("CREATE TYPE team_role_enum AS ENUM ('admin', 'editor', 'viewer')")

    # 2. Create shared_resource_type_enum
    op.execute(
        "CREATE TYPE shared_resource_type_enum AS ENUM "
        "('graph', 'note', 'flashcard', 'quiz', 'conversation', 'document')"
    )

    # 3. Create share_permission_enum
    op.execute(
        "CREATE TYPE share_permission_enum AS ENUM ('view', 'edit', 'admin')"
    )

    # 4. Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Index('idx_teams_owner_id', 'owner_id'),
        sa.Index('idx_teams_name', 'name'),
    )

    # 5. Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', postgresql.ENUM(name='team_role_enum', create_type=False), nullable=False, server_default='viewer'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
        sa.Index('idx_team_members_team_id', 'team_id'),
        sa.Index('idx_team_members_user_id', 'user_id'),
    )

    # 6. Create shared_resources table
    op.create_table(
        'shared_resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_type', postgresql.ENUM(name='shared_resource_type_enum', create_type=False), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=False),
        sa.Column('default_permission', postgresql.ENUM(name='share_permission_enum', create_type=False), nullable=False, server_default='view'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Index('idx_shared_resources_team', 'team_id'),
        sa.Index('idx_shared_resources_resource', 'resource_type', 'resource_id'),
        sa.Index('idx_shared_resources_shared_by', 'shared_by'),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('shared_resources')
    op.drop_table('team_members')
    op.drop_table('teams')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS share_permission_enum")
    op.execute("DROP TYPE IF EXISTS shared_resource_type_enum")
    op.execute("DROP TYPE IF EXISTS team_role_enum")
