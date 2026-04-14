import uuid
from sqlalchemy import String, Text, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
import enum

class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingStep(str, enum.Enum):
    QUEUED = "QUEUED"                    # Chờ trong hàng đợi
    INITIAL = "INITIAL"                  # Mặc định khi PENDING
    EXTRACTING = "EXTRACTING"            # Đang đọc PDF
    CHUNKING = "CHUNKING"                # Chia nhỏ văn bản
    EXTRACTING_ENTITIES = "EXTRACTING_ENTITIES"  # LLM trích xuất tri thức
    BUILDING_GRAPH = "BUILDING_GRAPH"    # Xây dựng quan hệ
    EMBEDDING = "EMBEDDING"              # Lưu vào Vector DB
    COMPLETED = "COMPLETED"              # Hoàn thành

class MediaType(str, enum.Enum):
    """Document media type — Sprint 17: Media Microlearning."""
    TEXT = "text"           # PDF, TXT, source code
    VIDEO = "video"         # YouTube video
    AUDIO = "audio"         # MP3, WAV, etc.

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    processing_step: Mapped[ProcessingStep] = mapped_column(
        Enum(ProcessingStep), default=ProcessingStep.INITIAL
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Sprint 17: Media Microlearning
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="mediatype", values_callable=lambda x: [e.value for e in x]),
        default=MediaType.TEXT,
        nullable=False,
        server_default="text"
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    quizzes = relationship("Quiz", back_populates="document")
    document_associations = relationship(
        "DocumentTopic", back_populates="document", cascade="all, delete-orphan"
    )
    topics = relationship(
        "Topic", secondary="document_topics", back_populates="documents"
    )
    entity_links = relationship(
        "EntityDocument", back_populates="document", cascade="all, delete-orphan"
    )
    transcripts = relationship(
        "Transcript", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_documents_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
