import uuid
from sqlalchemy import String, Text, Float, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin

class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )

    def __repr__(self):
        return f"<DocumentChunk(document_id={self.document_id}, chunk_index={self.chunk_index})>"

class GraphEntity(Base, TimestampMixin):
    __tablename__ = "graph_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    canonical_name: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    __table_args__ = (
        UniqueConstraint("document_id", "canonical_name", name="uq_document_entity_name"),
    )

    def __repr__(self):
        return f"<GraphEntity(canonical_name={self.canonical_name}, type={self.entity_type})>"

class GraphRelation(Base, TimestampMixin):
    __tablename__ = "graph_relations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    source_entity: Mapped[str] = mapped_column(String(255), index=True)
    target_entity: Mapped[str] = mapped_column(String(255), index=True)
    relation_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("document_id", "source_entity", "target_entity", "relation_type", name="uq_document_relation"),
        Index("idx_graph_relations_source", "source_entity"),
        Index("idx_graph_relations_target", "target_entity"),
    )

    def __repr__(self):
        return f"<GraphRelation(source={self.source_entity}, target={self.target_entity}, type={self.relation_type})>"
