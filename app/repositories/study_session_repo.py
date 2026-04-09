"""
StudySessionRepository providing data access for StudySession model.
"""
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime, timedelta

from ..models.flashcard import StudySession
from .base import BaseRepository


class StudySessionRepository(BaseRepository[StudySession]):
    """
    Repository for StudySession with analytics operations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, StudySession)

    async def create(
        self,
        user_id: uuid.UUID,
        flashcard_id: uuid.UUID,
        quality: int,
        time_taken_ms: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> StudySession:
        """Create a new study session record."""
        session_record = StudySession(
            user_id=user_id,
            flashcard_id=flashcard_id,
            quality=quality,
            time_taken_ms=time_taken_ms,
            idempotency_key=idempotency_key
        )
        self.session.add(session_record)
        await self.session.flush()
        await self.session.refresh(session_record)
        return session_record

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StudySession]:
        """Get study sessions for a user with optional date range filter."""
        query = select(StudySession).where(StudySession.user_id == user_id)
        if start_date:
            query = query.where(StudySession.reviewed_at >= start_date)
        if end_date:
            query = query.where(StudySession.reviewed_at <= end_date)
        query = query.order_by(StudySession.reviewed_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_idempotency_key(
        self,
        idempotency_key: str
    ) -> Optional[StudySession]:
        """Check if a review already exists with this idempotency key."""
        query = select(StudySession).where(
            StudySession.idempotency_key == idempotency_key
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_stats(
        self,
        user_id: uuid.UUID,
        days: int = 7
    ) -> dict:
        """
        Get study statistics for a user over the last N days.
        Returns: total_reviews, avg_quality, total_cards_reviewed, streak_days
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total reviews in period
        total_reviews_query = (
            select(func.count(StudySession.id))
            .where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.reviewed_at >= cutoff
                )
            )
        )
        total_reviews_result = await self.session.execute(total_reviews_query)
        total_reviews = total_reviews_result.scalar() or 0

        # Average quality
        avg_quality_query = (
            select(func.avg(StudySession.quality))
            .where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.reviewed_at >= cutoff
                )
            )
        )
        avg_quality_result = await self.session.execute(avg_quality_query)
        avg_quality = avg_quality_result.scalar() or 0.0

        # Unique cards reviewed
        cards_reviewed_query = (
            select(func.count(func.distinct(StudySession.flashcard_id)))
            .where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.reviewed_at >= cutoff
                )
            )
        )
        cards_reviewed_result = await self.session.execute(cards_reviewed_query)
        total_cards_reviewed = cards_reviewed_result.scalar() or 0

        # Calculate streak (consecutive days with at least 1 review)
        streak = await self._calculate_streak(user_id)

        return {
            "total_reviews": total_reviews,
            "avg_quality": round(float(avg_quality), 2),
            "total_cards_reviewed": total_cards_reviewed,
            "streak_days": streak
        }

    async def _calculate_streak(
        self,
        user_id: uuid.UUID
    ) -> int:
        """
        Calculate current streak (consecutive days with reviews).
        """
        # Get distinct review dates
        query = (
            select(func.distinct(func.date(StudySession.reviewed_at)))
            .where(StudySession.user_id == user_id)
            .order_by(func.date(StudySession.reviewed_at).desc())
        )
        result = await self.session.execute(query)
        review_dates = [row[0] for row in result.fetchall()]

        if not review_dates:
            return 0

        streak = 0
        today = datetime.utcnow().date()
        expected_date = today

        for date in review_dates:
            if date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif date < expected_date:
                # Gap detected, streak ends
                break

        return streak
