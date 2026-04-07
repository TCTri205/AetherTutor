import uuid
from sqlalchemy import String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin
import enum

class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingStep(str, enum.Enum):
    INITIAL = "INITIAL"                  # Mặc định khi PENDING
    EXTRACTING = "EXTRACTING"            # Đang đọc PDF
    CHUNKING = "CHUNKING"                # Chia nhỏ văn bản
    EXTRACTING_ENTITIES = "EXTRACTING_ENTITIES"  # LLM trích xuất tri thức
    BUILDING_GRAPH = "BUILDING_GRAPH"    # Xây dựng quan hệ
    EMBEDDING = "EMBEDDING"              # Lưu vào Vector DB
    COMPLETED = "COMPLETED"              # Hoàn thành

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
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

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
