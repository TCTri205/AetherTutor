"""
NoteService for Stage 2 - Zettelkasten & Bi-directional Linking

Service layer for note CRUD operations and backlink suggestions.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.repositories.note_repo import NoteRepository, NoteLinkRepository
from app.repositories.note_entity_link_repo import NoteEntityLinkRepository
from app.services.backlink_ai_service import BacklinkAIService
from app.models.note import Note, NoteLink
from app.models.note_entity_link import NoteEntityLink
from app.constants import NOTE_LINK_SUGGESTION_THRESHOLD

logger = logging.getLogger(__name__)


class NoteService:
    """
    Service for managing notes in the Zettelkasten system.

    Provides:
    - Note CRUD operations
    - Backlink suggestions (AI-powered)
    - Note graph generation for visualization
    - P1-2: Auto entity linking khi tạo note (Zettelkasten)
    """

    def __init__(
        self,
        note_repo: NoteRepository,
        note_link_repo: NoteLinkRepository,
        backlink_ai_service: BacklinkAIService,
        # P1-2: Thêm dependencies cho auto entity linking
        note_entity_link_repo: Optional[NoteEntityLinkRepository] = None,
    ):
        self.note_repo = note_repo
        self.note_link_repo = note_link_repo
        self.backlink_ai = backlink_ai_service
        # P1-2
        self.note_entity_link_repo = note_entity_link_repo

    async def create_note(
        self,
        user_id: uuid.UUID,
        title: str,
        content: str,
        note_type: str = "literature",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        auto_link_entities: bool = True,  # P1-2: Flag để bật/tắt auto linking
    ) -> Note:
        """
        Create a new atomic note.
        
        P1-2: Tự động extract và match entities từ graph, tạo links nếu confidence cao.
        """
        note = await self.note_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            note_type=note_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        # P1-2: Auto entity linking
        if auto_link_entities and self.note_entity_link_repo:
            try:
                await self._auto_link_to_entities(note, user_id)
            except Exception as e:
                # Log error nhưng không fail note creation
                logger.warning(f"Auto entity linking failed for note {note.id}: {e}")
        
        return note

    async def _auto_link_to_entities(self, note: Note, user_id: uuid.UUID) -> List[NoteEntityLink]:
        """
        P1-2: Tự động tìm và link note tới graph entities liên quan.
        
        Workflow:
        1. Dùng BacklinkAIService.find_related_entities() để tìm entities phù hợp
        2. Với entities có confidence >= threshold → auto-create links
        3. Với entities có confidence thấp → chỉ log, không tạo link
        
        Returns:
            List of NoteEntityLink đã tạo
        """
        # Bước 1: Tìm entities liên quan qua AI + embedding
        related_entities = await self.backlink_ai.find_related_entities(
            note_content=note.content,
            user_id=user_id,
            top_k=10,
        )
        
        if not related_entities:
            logger.debug(f"No related entities found for note {note.id}")
            return []
        
        # Bước 2: Auto-create links cho entities có confidence cao
        created_links = []
        for entity_suggestion in related_entities:
            if entity_suggestion.confidence < NOTE_LINK_SUGGESTION_THRESHOLD:
                # Confidence thấp → skip
                logger.debug(
                    f"Entity {entity_suggestion.entity_name} confidence "
                    f"{entity_suggestion.confidence:.2f} < threshold "
                    f"{NOTE_LINK_SUGGESTION_THRESHOLD}, skipping"
                )
                continue
            
            # Check nếu link đã tồn tại
            existing = await self.note_entity_link_repo.get_by_note_and_entity(
                note_id=note.id,
                entity_id=entity_suggestion.entity_id
            )
            
            if existing:
                logger.debug(f"Link already exists: note {note.id} -> entity {entity_suggestion.entity_id}")
                continue
            
            # Tạo link mới
            try:
                link = await self.note_entity_link_repo.create(
                    user_id=user_id,
                    note_id=note.id,
                    entity_id=entity_suggestion.entity_id,
                    match_type="ai_suggested",
                    confidence=entity_suggestion.confidence,
                    context=entity_suggestion.context,
                )
                created_links.append(link)
                logger.info(
                    f"Auto-linked note {note.id} to entity {entity_suggestion.entity_name} "
                    f"(confidence={entity_suggestion.confidence:.2f})"
                )
            except Exception as e:
                # Lỗi khi tạo link (có thể do unique constraint) → log và tiếp tục
                logger.warning(f"Failed to create entity link: {e}")
                continue
        
        if created_links:
            logger.info(
                f"Created {len(created_links)} auto entity links for note {note.id}"
            )
        
        return created_links

    async def get_note(
        self, note_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Note]:
        """Get a single note by ID (with ownership check)."""
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return None
        return note

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
        auto_link_entities: bool = True,  # Re-trigger entity linking on update
    ) -> Optional[Note]:
        """
        Update note fields and trigger backlink re-suggestion.
        Returns updated note or None if not found.

        BR-009: Nếu content thay đổi → re-run auto entity linking.
        """
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return None

        content_changed = content is not None and content != note.content

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags

        await self.note_repo.session.commit()
        await self.note_repo.session.refresh(note)

        # BR-009: Re-run entity linking nếu content thay đổi
        if content_changed and auto_link_entities and self.note_entity_link_repo:
            try:
                await self._auto_link_to_entities(note, user_id)
            except Exception as e:
                logger.warning(f"Auto entity linking failed on update for note {note.id}: {e}")

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
        self, user_id: uuid.UUID, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Get the note graph for Zettelkasten visualization with pagination.

        Returns:
        {
            "nodes": [{"id", "title", "note_type", "tags", "created_at"}],
            "edges": [{"source", "target", "link_type", "context"}]
        }
        """
        return await self.note_link_repo.get_note_graph(user_id, limit=limit)
