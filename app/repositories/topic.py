"""
TopicRepository — CRUD operations for Topic model (v1.2).
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.document_topic import DocumentTopic
from app.models.note_topic import NoteTopic
from app.repositories.base import BaseRepository


class TopicRepository(BaseRepository[Topic]):
    """Repository for Topic model with junction table helpers."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Topic)

    async def get_by_id_and_user(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Topic]:
        """Get topic by ID, verifying ownership."""
        stmt = select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(
        self, user_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Topic]:
        """List topics for a user with pagination."""
        stmt = (
            select(Topic)
            .where(Topic.user_id == user_id)
            .order_by(Topic.sort_order, Topic.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Topic:
        """Create a new topic. Raises ValueError if slug duplicate."""
        topic = Topic(**kwargs)
        self.session.add(topic)
        try:
            await self.session.flush()
            return topic
        except IntegrityError as e:
            await self.session.rollback()
            if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                raise ValueError("Topic name already exists") from e
            raise

    async def update(self, topic_id: uuid.UUID, **kwargs) -> Optional[Topic]:
        """Update topic fields."""
        topic = await self.get_by_id(topic_id)
        if not topic:
            return None
        for key, value in kwargs.items():
            if hasattr(topic, key):
                setattr(topic, key, value)
        await self.session.flush()
        return topic

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count topics for a user."""
        stmt = (
            select(func.count())
            .select_from(Topic)
            .where(Topic.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # --- Junction table helpers ---

    async def add_document(
        self, topic_id: uuid.UUID, document_id: uuid.UUID, is_primary: bool = False
    ) -> DocumentTopic:
        """Add document to topic."""
        junction = DocumentTopic(
            topic_id=topic_id,
            document_id=document_id,
            is_primary=is_primary,
        )
        self.session.add(junction)
        await self.session.flush()
        return junction

    async def remove_document(
        self, topic_id: uuid.UUID, document_id: uuid.UUID
    ) -> bool:
        """Remove document from topic."""
        stmt = delete(DocumentTopic).where(
            DocumentTopic.topic_id == topic_id,
            DocumentTopic.document_id == document_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore[return-value]

    async def add_note(self, topic_id: uuid.UUID, note_id: uuid.UUID) -> NoteTopic:
        """Add note to topic."""
        junction = NoteTopic(topic_id=topic_id, note_id=note_id)
        self.session.add(junction)
        await self.session.flush()
        return junction

    async def remove_note(
        self, topic_id: uuid.UUID, note_id: uuid.UUID
    ) -> bool:
        """Remove note from topic."""
        stmt = delete(NoteTopic).where(
            NoteTopic.topic_id == topic_id,
            NoteTopic.note_id == note_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore[return-value]

    async def get_documents_for_topic(
        self, topic_id: uuid.UUID
    ) -> list:
        """Get all documents for a topic."""
        from app.models.document import Document

        stmt = (
            select(Document)
            .join(DocumentTopic, Document.id == DocumentTopic.document_id)
            .where(DocumentTopic.topic_id == topic_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_notes_for_topic(self, topic_id: uuid.UUID) -> list:
        """Get all notes for a topic."""
        from app.models.note import Note

        stmt = (
            select(Note)
            .join(NoteTopic, Note.id == NoteTopic.note_id)
            .where(NoteTopic.topic_id == topic_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
