"""
FlashcardRepository providing data access for Flashcard model.
"""
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime

from ..models.flashcard import Flashcard
from .base import BaseRepository


class FlashcardRepository(BaseRepository[Flashcard]):
    """
    Repository for Flashcard with SM-2 specific operations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Flashcard)

    async def create(
        self,
        user_id: uuid.UUID,
        front: str,
        back: str,
        document_id: Optional[uuid.UUID] = None,
        source: str = "manual",
        metadata: Optional[dict] = None
    ) -> Flashcard:
        """Create a new flashcard."""
        flashcard = Flashcard(
            user_id=user_id,
            front=front,
            back=back,
            document_id=document_id,
            source=source,
            card_metadata=metadata or {}
        )
        self.session.add(flashcard)
        await self.session.flush()
        await self.session.refresh(flashcard)
        return flashcard

    async def bulk_create(
        self,
        flashcards: List[Flashcard]
    ) -> List[Flashcard]:
        """Bulk create flashcards."""
        self.session.add_all(flashcards)
        await self.session.flush()
        for fc in flashcards:
            await self.session.refresh(fc)
        return flashcards

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        source: Optional[str] = None
    ) -> List[Flashcard]:
        """Get flashcards for a user with pagination."""
        query = select(Flashcard).where(Flashcard.user_id == user_id)
        if source:
            query = query.where(Flashcard.source == source)
        query = query.order_by(Flashcard.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_due_cards(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        include_overdue: bool = True
    ) -> List[Flashcard]:
        """
        Get flashcards due for review.
        Cards where sm2_next_review <= NOW()
        """
        query = (
            select(Flashcard)
            .where(
                and_(
                    Flashcard.user_id == user_id,
                    Flashcard.sm2_next_review <= func.now()
                )
            )
            .order_by(Flashcard.sm2_next_review.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_due_cards_count(self, user_id: uuid.UUID) -> int:
        """Count flashcards due for review."""
        query = (
            select(func.count(Flashcard.id))
            .where(
                and_(
                    Flashcard.user_id == user_id,
                    Flashcard.sm2_next_review <= func.now()
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update_sm2_params(
        self,
        card_id: uuid.UUID,
        ease_factor: float,
        interval: int,
        repetitions: int,
        next_review: datetime
    ) -> Optional[Flashcard]:
        """Update SM-2 parameters for a flashcard."""
        flashcard = await self.get_by_id(card_id)
        if flashcard:
            flashcard.sm2_ease_factor = ease_factor
            flashcard.sm2_interval = interval
            flashcard.sm2_repetitions = repetitions
            flashcard.sm2_next_review = next_review
            await self.session.flush()
            await self.session.refresh(flashcard)
        return flashcard

    async def delete_by_user(
        self,
        user_id: uuid.UUID,
        card_id: uuid.UUID
    ) -> bool:
        """Delete a flashcard only if it belongs to the user."""
        flashcard = await self.get_by_id(card_id)
        if flashcard and flashcard.user_id == user_id:
            await self.session.delete(flashcard)
            await self.session.flush()
            return True
        return False

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count total flashcards for a user."""
        query = select(func.count(Flashcard.id)).where(Flashcard.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0
