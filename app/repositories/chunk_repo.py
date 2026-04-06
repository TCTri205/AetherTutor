from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from ..models.graph import DocumentChunk
from typing import List
import uuid

class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, chunks: List[DocumentChunk]):
        self.session.add_all(chunks)
        await self.session.flush()

    async def delete_by_document_id(self, document_id: uuid.UUID):
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await self.session.flush()
