"""
NoteService for Stage 2 - Zettelkasten & Bi-directional Linking

Service layer for note CRUD operations and backlink suggestions.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.repositories.note_repo import NoteRepository, NoteLinkRepository
from app.services.backlink_ai_service import BacklinkAIService
from app.models.note import Note, NoteLink

logger = logging.getLogger(__name__)


class NoteService:
    """
    Service for managing notes in the Zettelkasten system.
    
    Provides:
    - Note CRUD operations
    - Backlink suggestions (AI-powered)
    - Note graph generation for visualization
    """

    def __init__(
        self,
        note_repo: NoteRepository,
        note_link_repo: NoteLinkRepository,
        backlink_ai_service: BacklinkAIService,
    ):
        self.note_repo = note_repo
        self.note_link_repo = note_link_repo
        self.backlink_ai = backlink_ai_service

    async def create_note(
        self,
        user_id: uuid.UUID,
        title: str,
        content: str,
        note_type: str = "literature",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Note:
        """Create a new atomic note."""
        note = await self.note_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            note_type=note_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        return note

    async def get_note(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Note]:
        """Get a single note by ID (with ownership check)."""
        return await self.note_repo.get(note_id)

    async def get_note_detail(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Note]:
        """Get note detail with backlinks."""
        return await self.note_repo.get_by_id_with_links(note_id, user_id)

    async def list_notes(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        note_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Tuple[List[Note], int]:
        """List user's notes with filters."""
        if tags:
            return await self.note_repo.search_by_tags(
                user_id=user_id, tags=tags, skip=skip, limit=limit
            )
        return await self.note_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            note_type=note_type,
        )

    async def update_note(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Note]:
        """
        Update note fields and trigger backlink re-suggestion.
        Returns updated note or None if not found.
        """
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return None

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags

        await self.note_repo.session.commit()
        await self.note_repo.session.refresh(note)

        return note

    async def delete_note(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a note (cascades to links)."""
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return False

        await self.note_repo.delete(note_id)
        return True

    async def create_link(
        self,
        user_id: uuid.UUID,
        source_note_id: uuid.UUID,
        target_note_id: uuid.UUID,
        context: Optional[str] = None,
        link_type: str = "manual",
    ) -> Optional[NoteLink]:
        """Create a link between two notes."""
        # Verify both notes exist and belong to user
        source = await self.note_repo.get(source_note_id)
        target = await self.note_repo.get(target_note_id)
        
        if not source or not target:
            return None
        if source.user_id != user_id or target.user_id != user_id:
            return None

        # Check if link already exists
        existing = await self.note_link_repo.get_link(
            source_note_id, target_note_id, user_id
        )
        if existing:
            return existing

        link = await self.note_link_repo.create_link(
            user_id=user_id,
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            context=context,
            link_type=link_type,
        )
        return link

    async def get_backlinks(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[NoteLink]:
        """Get incoming links to a note (backlinks)."""
        return await self.note_link_repo.get_backlinks(note_id, user_id)

    async def get_outgoing_links(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[NoteLink]:
        """Get outgoing links from a note."""
        return await self.note_link_repo.get_outgoing_links(note_id, user_id)

    async def suggest_backlinks(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get AI-powered backlink suggestions for a note.
        
        Returns:
        {
            "related_entities": [...],
            "related_notes": [...]
        }
        """
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return {"related_entities": [], "related_notes": []}

        suggestions = await self.backlink_ai.suggest_backlinks_for_note(
            note_id=note_id,
            user_id=user_id,
        )

        return suggestions.dict()

    async def get_note_graph(
        self, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get the entire note graph for Zettelkasten visualization.
        
        Returns:
        {
            "nodes": [{"id", "title", "note_type", "tags", "created_at"}],
            "edges": [{"source", "target", "link_type", "context"}]
        }
        """
        return await self.note_link_repo.get_note_graph(user_id)
