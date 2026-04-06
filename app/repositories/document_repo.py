from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.document import Document, DocumentStatus
from typing import Optional
import uuid

class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, filename: str, content_hash: str) -> Document:
        doc = Document(
            filename=filename,
            content_hash=content_hash,
            status=DocumentStatus.PENDING
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
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalars().first()

    async def update_status(self, document_id: uuid.UUID, status: DocumentStatus, error_message: Optional[str] = None):
        doc = await self.get_by_id(document_id)
        if doc:
            doc.status = status
            doc.error_message = error_message
            await self.session.flush()
        return doc
