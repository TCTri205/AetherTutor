"""
Note & NoteLink repositories for Stage 2 - Zettelkasten & Bi-directional Linking
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.models.note import Note, NoteLink
from .base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository for Note model with Zettelkasten operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Note)

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        content: str,
        note_type: str = "literature",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Note:
        """Create a new note."""
        note = Note(
            user_id=user_id,
            title=title,
            content=content,
            note_type=note_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        note_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Tuple[List[Note], int]:
        """List user's notes with optional filters."""
        query = select(Note).where(Note.user_id == user_id)

        if note_type:
            query = query.where(Note.note_type == note_type)
        if tags:
            # Notes that have ANY of the specified tags
            query = query.where(Note.tags.overlap(tags))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(Note.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        notes = result.scalars().all()
        return notes, total

    async def get_by_id_with_links(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Note]:
        """Get note by ID with outgoing and incoming links."""
        query = (
            select(Note)
            .where(Note.id == note_id, Note.user_id == user_id)
            .options(
                selectinload(Note.outgoing_links).selectinload(NoteLink.target_note),
                selectinload(Note.incoming_links).selectinload(NoteLink.source_note),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def search_by_tags(
        self, user_id: uuid.UUID, tags: List[str], skip: int = 0, limit: int = 50
    ) -> Tuple[List[Note], int]:
        """Search notes by tags (matches ANY of the tags)."""
        query = select(Note).where(
            Note.user_id == user_id,
            Note.tags.overlap(tags),
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(Note.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        notes = result.scalars().all()
        return notes, total

    async def search_by_content(
        self, user_id: uuid.UUID, query_text: str, skip: int = 0, limit: int = 50
    ) -> Tuple[List[Note], int]:
        """Search notes by title/content (ILIKE)."""
        search_pattern = f"%{query_text}%"
        query = select(Note).where(
            Note.user_id == user_id,
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(Note.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        notes = result.scalars().all()
        return notes, total

    async def get_notes_for_backlink_suggestion(
        self, user_id: uuid.UUID, exclude_note_id: uuid.UUID, limit: int = 20
    ) -> List[Note]:
        """Get notes for backlink suggestion (recent notes excluding current)."""
        query = (
            select(Note)
            .where(Note.user_id == user_id, Note.id != exclude_note_id)
            .order_by(desc(Note.updated_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class NoteLinkRepository(BaseRepository[NoteLink]):
    """Repository for NoteLink model with backlink operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, NoteLink)

    async def create_link(
        self,
        user_id: uuid.UUID,
        source_note_id: uuid.UUID,
        target_note_id: uuid.UUID,
        context: Optional[str] = None,
        link_type: str = "manual",
    ) -> NoteLink:
        """Create a link between two notes."""
        link = NoteLink(
            user_id=user_id,
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            context=context,
            link_type=link_type,
        )
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        return link

    async def bulk_create_links(
        self, links: List[NoteLink]
    ) -> List[NoteLink]:
        """Bulk create links (for AI-suggested backlinks)."""
        self.session.add_all(links)
        await self.session.flush()
        return links

    async def get_backlinks(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[NoteLink]:
        """Get incoming links to a note (backlinks)."""
        query = (
            select(NoteLink)
            .where(
                NoteLink.target_note_id == note_id,
                NoteLink.user_id == user_id,
            )
            .options(selectinload(NoteLink.source_note))
            .order_by(desc(NoteLink.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_outgoing_links(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[NoteLink]:
        """Get outgoing links from a note."""
        query = (
            select(NoteLink)
            .where(
                NoteLink.source_note_id == note_id,
                NoteLink.user_id == user_id,
            )
            .options(selectinload(NoteLink.target_note))
            .order_by(desc(NoteLink.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_link(
        self, source_note_id: uuid.UUID, target_note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[NoteLink]:
        """Check if a link exists between two notes."""
        query = select(NoteLink).where(
            NoteLink.source_note_id == source_note_id,
            NoteLink.target_note_id == target_note_id,
            NoteLink.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def delete_link(
        self, link_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a link (with ownership check)."""
        link = await self.get(link_id)
        if not link or link.user_id != user_id:
            return False
        await self.delete(link_id)
        return True

    async def get_note_graph(
        self, user_id: uuid.UUID, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Get the note graph for visualization with pagination.

        Args:
            user_id: User UUID
            limit: Maximum number of nodes to return (prevents memory overload)

        Returns: {nodes: [...], edges: [...]}
        """
        # Get limited notes
        notes_query = (
            select(Note)
            .where(Note.user_id == user_id)
            .limit(limit)
        )
        notes_result = await self.session.execute(notes_query)
        notes = notes_result.scalars().all()

        if not notes:
            return {"nodes": [], "edges": []}

        # Only fetch links for the notes we retrieved
        note_ids = [note.id for note in notes]
        links_query = (
            select(NoteLink)
            .where(
                NoteLink.user_id == user_id,
                (NoteLink.source_note_id.in_(note_ids)) |
                (NoteLink.target_note_id.in_(note_ids))
            )
        )
        links_result = await self.session.execute(links_query)
        links = links_result.scalars().all()

        nodes = [
            {
                "id": str(note.id),
                "title": note.title,
                "note_type": note.note_type,
                "tags": note.tags,
                "created_at": note.created_at.isoformat(),
            }
            for note in notes
        ]

        edges = [
            {
                "source": str(link.source_note_id),
                "target": str(link.target_note_id),
                "link_type": link.link_type,
                "context": link.context,
            }
            for link in links
        ]

        return {"nodes": nodes, "edges": edges}
