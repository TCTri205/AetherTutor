"""
NoteEntityLinkRepository - Data access layer for note-entity links.

P1-2: Repository để quản lý auto entity linking khi tạo notes.
"""

import uuid
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note_entity_link import NoteEntityLink


class NoteEntityLinkRepository:
    """Repository cho note-entity links."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        note_id: uuid.UUID,
        entity_id: uuid.UUID,
        match_type: str = "ai_suggested",
        confidence: Optional[float] = None,
        context: Optional[str] = None,
    ) -> NoteEntityLink:
        """Tạo note-entity link mới."""
        link = NoteEntityLink(
            user_id=user_id,
            note_id=note_id,
            entity_id=entity_id,
            match_type=match_type,
            confidence=confidence,
            context=context,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_by_note_and_entity(
        self,
        note_id: uuid.UUID,
        entity_id: uuid.UUID,
    ) -> Optional[NoteEntityLink]:
        """Check nếu link đã tồn tại."""
        stmt = select(NoteEntityLink).where(
            and_(
                NoteEntityLink.note_id == note_id,
                NoteEntityLink.entity_id == entity_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_note(self, note_id: uuid.UUID) -> List[NoteEntityLink]:
        """Lấy tất cả entity links của một note."""
        stmt = (
            select(NoteEntityLink)
            .where(NoteEntityLink.note_id == note_id)
            .order_by(NoteEntityLink.confidence.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_note(self, note_id: uuid.UUID) -> int:
        """Xóa tất cả entity links của một note."""
        stmt = select(NoteEntityLink).where(
            NoteEntityLink.note_id == note_id
        )
        result = await self.session.execute(stmt)
        links = list(result.scalars().all())
        
        for link in links:
            await self.session.delete(link)
        
        return len(links)
