"""Add conversations and messages

Revision ID: 5f4b730b3577
Revises: 201010a811fc
Create Date: 2026-04-07 08:47:52.806819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f4b730b3577'
down_revision: Union[str, Sequence[str], None] = '201010a811fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create MessageStatus Enum type
    messagestatus = postgresql.ENUM('PENDING', 'COMPLETED', 'FAILED', name='messagestatus')
    messagestatus.create(op.get_bind())

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sequence_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', name='messagestatus'), nullable=False),
        sa.Column('context_used', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', 'sequence_index', name='uq_conversation_message_seq')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('messages')
    
    # Drop MessageStatus ENUM
    messagestatus = postgresql.ENUM('PENDING', 'COMPLETED', 'FAILED', name='messagestatus')
    messagestatus.drop(op.get_bind())
    
    op.drop_table('conversations')
