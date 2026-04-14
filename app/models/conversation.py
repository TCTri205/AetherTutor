import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, Enum, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class MessageStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="Cuộc hội thoại mới")
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    # BR-006: Metadata cho pedagogical state tracking
    metadata_: Mapped[dict | None] = mapped_column(JSON, nullable=True, server_default='{}', name="metadata")

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sequence_index"
    )

    __table_args__ = (
        Index("idx_conversations_document_id", "document_id"),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), 
        nullable=False
    )
    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    sequence_index: Mapped[int] = mapped_column(Integer)
    
    # Advanced fields from V4.2
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), 
        default=MessageStatus.COMPLETED
    )
    context_used: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_index", name="uq_conversation_message_seq"),
        Index("idx_messages_conversation_id", "conversation_id"),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, sequence={self.sequence_index})>"
