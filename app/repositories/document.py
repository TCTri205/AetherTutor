"""
DocumentRepository — CRUD operations for Document model.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Document)

    async def get_by_id_and_user(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Document]:
        """Get document by ID, verifying ownership."""
        stmt = select(Document).where(
            Document.id == document_id, Document.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
