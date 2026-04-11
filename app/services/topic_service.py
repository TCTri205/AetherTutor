"""
TopicService — Topic management with document/note assignment (v1.2).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from loguru import logger
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.repositories.topic import TopicRepository


class TopicService:
    """Topic management service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.topic_repo = TopicRepository(session)

    async def create_topic(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str | None = None,
        color: str = "#3B82F6",
        icon: str | None = None,
    ) -> Topic:
        """Create a new topic with auto-generated slug."""
        slug = slugify(name)
        if not slug:
            raise ValueError("Topic name is invalid")

        topic = await self.topic_repo.create(
            user_id=user_id,
            name=name,
            slug=slug,
            description=description,
            color=color,
            icon=icon,
        )
        await self.session.commit()
        await self.session.refresh(topic)

        logger.info(f"Topic created: {name} ({topic.id}) for user {user_id}")
        return topic

    async def get_topic(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Topic]:
        """Get topic by ID, verifying ownership."""
        return await self.topic_repo.get_by_id_and_user(topic_id, user_id)

    async def list_topics(
        self, user_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Topic]:
        """List all topics for a user."""
        return await self.topic_repo.list_by_user(user_id, limit, offset)

    async def update_topic(
        self,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[Topic]:
        """Update topic fields."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return None

        # Auto-regenerate slug if name changes
        if "name" in kwargs:
            kwargs["slug"] = slugify(kwargs["name"])
            if not kwargs["slug"]:
                raise ValueError("Topic name is invalid")

        try:
            updated = await self.topic_repo.update(topic_id, **kwargs)
            await self.session.commit()
            if updated:
                await self.session.refresh(updated)
            logger.info(f"Topic updated: {topic_id}")
            return updated
        except ValueError as e:
            await self.session.rollback()
            raise

    async def archive_topic(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Topic]:
        """Archive a topic (soft delete)."""
        from datetime import datetime, timezone

        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return None

        updated = await self.topic_repo.update(
            topic_id, is_archived=True, archived_at=datetime.now(timezone.utc)
        )
        await self.session.commit()
        if updated:
            await self.session.refresh(updated)

        logger.info(f"Topic archived: {topic_id}")
        return updated

    async def delete_topic(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a topic. Junction rows cascade delete, documents/notes remain."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return False

        await self.topic_repo.delete(topic_id)
        await self.session.commit()
        logger.info(f"Topic deleted: {topic_id}")
        return True

    async def add_document(
        self,
        topic_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        """Add document to topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            raise ValueError("Topic not found")

        # Verify document ownership (basic check via doc repo)
        from app.repositories.document import DocumentRepository

        doc_repo = DocumentRepository(self.session)
        doc = await doc_repo.get_by_id_and_user(document_id, user_id)
        if not doc:
            raise ValueError("Document not found")

        await self.topic_repo.add_document(
            topic_id, document_id, is_primary
        )
        await self.session.commit()

        logger.info(f"Document {document_id} added to topic {topic_id}")
        return {"topic_id": topic_id, "document_id": document_id}

    async def remove_document(
        self,
        topic_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove document from topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return False

        result = await self.topic_repo.remove_document(topic_id, document_id)
        await self.session.commit()
        return result

    async def add_note(
        self,
        topic_id: uuid.UUID,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Add note to topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            raise ValueError("Topic not found")

        await self.topic_repo.add_note(topic_id, note_id)
        await self.session.commit()

        logger.info(f"Note {note_id} added to topic {topic_id}")
        return {"topic_id": topic_id, "note_id": note_id}

    async def remove_note(
        self,
        topic_id: uuid.UUID,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove note from topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return False

        result = await self.topic_repo.remove_note(topic_id, note_id)
        await self.session.commit()
        return result

    async def get_topic_documents(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> list:
        """Get all documents for a topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return []
        return await self.topic_repo.get_documents_for_topic(topic_id)

    async def get_topic_notes(
        self, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> list:
        """Get all notes for a topic."""
        topic = await self.topic_repo.get_by_id_and_user(topic_id, user_id)
        if not topic:
            return []
        return await self.topic_repo.get_notes_for_topic(topic_id)
