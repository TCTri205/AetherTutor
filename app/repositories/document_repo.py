from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.document import Document, DocumentStatus, ProcessingStep
from ..models.graph import GraphEntity, GraphRelation
from typing import Optional, List, Tuple
import uuid
from .base import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Document)

    async def create(self, filename: str, content_hash: str) -> Document:
        doc = Document(
            filename=filename,
            content_hash=content_hash,
            status=DocumentStatus.PENDING,
            processing_step=ProcessingStep.INITIAL
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_by_hash(self, content_hash: str) -> Optional[Document]:
        result = await self.session.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        return result.scalars().first()

    async def get_by_filename(self, filename: str) -> Optional[Document]:
        result = await self.session.execute(
            select(Document).where(Document.filename == filename)
        )
        return result.scalars().first()

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        return await super().get_by_id(document_id)

    async def update_status(self, document_id: uuid.UUID, status: DocumentStatus, error_message: Optional[str] = None):
        doc = await self.get_by_id(document_id)
        if doc:
            doc.status = status
            doc.error_message = error_message
            if status == DocumentStatus.COMPLETED:
                doc.processing_step = ProcessingStep.COMPLETED
            await self.session.flush()
        return doc

    async def update_processing_step(self, document_id: uuid.UUID, step: ProcessingStep):
        doc = await self.get_by_id(document_id)
        if doc:
            doc.processing_step = step
            await self.session.flush()
        return doc

    async def update_file_path(self, document_id: uuid.UUID, file_path: str):
        doc = await self.get_by_id(document_id)
        if doc:
            doc.file_path = file_path
            await self.session.flush()
        return doc

    async def list_with_counts(self, skip: int = 0, limit: int = 100) -> List[Tuple[Document, int, int]]:
        """
        Fetch documents with entity/relation counts in a single query.
        Uses correlated subqueries to avoid Cartesian product from double JOIN
        (m entities × n relations = m*n rows would inflate counts).
        """
        entity_count_sq = (
            select(func.count(GraphEntity.id))
            .where(GraphEntity.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )
        relation_count_sq = (
            select(func.count(GraphRelation.id))
            .where(GraphRelation.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )

        stmt = (
            select(
                Document,
                func.coalesce(entity_count_sq, 0).label("entity_count"),
                func.coalesce(relation_count_sq, 0).label("relation_count")
            )
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.all())  # List of (Document, entity_count, relation_count)

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        result = await self.session.execute(
            select(self.model).order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, document_id: uuid.UUID) -> bool:
        return await super().delete(document_id)
