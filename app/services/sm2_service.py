"""
SM-2 Service - Spaced Repetition Algorithm

Implement thuật toán SM-2 (SuperMemo 2) cho flashcard review scheduling.
Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2

SM-2 Algorithm:
1. Sau mỗi review, user đánh giá quality (0-5):
   - 0: Complete blackout
   - 1: Incorrect response, correct one looked easy
   - 2: Correct response, but required significant effort
   - 3: Correct response, but required some thought
   - 4: Correct response, but hesitated
   - 5: Perfect response

2. Update rules:
   - Nếu quality < 3: repetitions = 0, interval = 0 (review lại ngay lập tức)
   - Nếu quality >= 3:
     - Nếu repetitions == 0: interval = 1
     - Nếu repetitions == 1: interval = 6
     - Nếu repetitions > 1: interval = interval * ease_factor
   - ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
   - ease_factor không được nhỏ hơn 1.3
   - repetitions += 1 (nếu quality >= 3)
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.constants import (
    SM2_MIN_EASE,
)


class SM2Service:
    """
    Service quản lý thuật toán SM-2 cho flashcard review.
    """
    
    @staticmethod
    def calculate_sm2_update(
        current_ease: float,
        current_interval: int,
        current_repetitions: int,
        quality: int,
    ) -> Dict[str, Any]:
        """
        Tính toán SM-2 update sau khi review.
        
        Args:
            current_ease: Ease factor hiện tại
            current_interval: Interval hiện tại (ngày)
            current_repetitions: Số lần lặp lại thành công liên tiếp
            quality: Quality rating (0-5)
            
        Returns:
            Dict với {ease_factor, interval, repetitions, next_review}
        """
        # Clamp quality
        quality = max(0, min(5, quality))
        
        # Tính ease factor mới
        new_ease = current_ease + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )
        new_ease = max(SM2_MIN_EASE, new_ease)  # Không nhỏ hơn 1.3
        
        if quality < 3:
            # Review không đạt → reset
            new_repetitions = 0
            new_interval = 0  # Review lại ngay lập tức (interval = 0 → next_review = NOW)
        else:
            # Review thành công
            new_repetitions = current_repetitions + 1
            
            if new_repetitions == 1:
                new_interval = 1
            elif new_repetitions == 2:
                new_interval = 6
            else:
                new_interval = round(current_interval * new_ease)
        
        # Tính next review date
        next_review = datetime.utcnow() + timedelta(days=new_interval)
        
        return {
            "ease_factor": round(new_ease, 2),
            "interval": new_interval,
            "repetitions": new_repetitions,
            "next_review": next_review,
        }
    
    async def review_flashcard(
        self,
        db: AsyncSession,
        card_id: uuid.UUID,
        quality: int,
        user_id: uuid.UUID,
        idempotency_key: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Review một flashcard và cập nhật SM-2 parameters.
        
        Args:
            db: Database session
            card_id: Flashcard ID
            quality: Quality rating (0-5)
            user_id: User ID (để verify ownership)
            idempotency_key: Key để chống duplicate review
            response_time_ms: Thời gian trả lời (ms)
            
        Returns:
            Dict với kết quả review
            
        Raises:
            ValueError: Nếu card không tồn tại hoặc không thuộc về user
        """
        # Import trong method để tránh circular imports
        from app.models.flashcard import Flashcard, StudySession
        
        # Kiểm tra idempotency
        if idempotency_key:
            from app.core.redis_client import get_redis_client
            redis = get_redis_client()
            cache_key = f"idempotency:review:{idempotency_key}"
            
            cached = await redis.get(cache_key)
            if cached:
                logger.info(f"Idempotent review hit: {idempotency_key}")
                import json
                return json.loads(cached)
        
        # Lấy flashcard
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.id == card_id,
                Flashcard.user_id == user_id,
            )
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise ValueError(f"Flashcard {card_id} không tồn tại hoặc không thuộc về bạn")
        
        # Tính SM-2 update
        update = self.calculate_sm2_update(
            current_ease=card.sm2_ease_factor,
            current_interval=card.sm2_interval,
            current_repetitions=card.sm2_repetitions,
            quality=quality,
        )
        
        # Cập nhật flashcard
        card.sm2_ease_factor = update["ease_factor"]
        card.sm2_interval = update["interval"]
        card.sm2_repetitions = update["repetitions"]
        card.sm2_next_review = update["next_review"]
        
        # Tạo study session record
        session = StudySession(
            user_id=user_id,
            flashcard_id=card_id,
            quality=quality,
            response_time_ms=response_time_ms,
        )
        db.add(session)
        
        await db.commit()
        await db.refresh(card)
        
        result_data = {
            "card_id": str(card_id),
            "quality": quality,
            "ease_factor": update["ease_factor"],
            "interval": update["interval"],
            "repetitions": update["repetitions"],
            "next_review": update["next_review"].isoformat(),
        }
        
        # Cache idempotency
        if idempotency_key:
            from app.core.redis_client import get_redis_client
            redis = get_redis_client()
            cache_key = f"idempotency:review:{idempotency_key}"
            import json
            await redis.setex(cache_key, 86400, json.dumps(result_data))  # 24h TTL
        
        logger.info(
            f"Flashcard {card_id} reviewed: quality={quality}, "
            f"interval={update['interval']}d, repetitions={update['repetitions']}"
        )
        
        return result_data
    
    async def get_due_cards(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách flashcards cần ôn tập.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Số cards tối đa trả về
            
        Returns:
            List của flashcard dicts
        """
        from app.models.flashcard import Flashcard
        
        now = datetime.utcnow()
        
        result = await db.execute(
            select(Flashcard)
            .where(
                Flashcard.user_id == user_id,
                Flashcard.sm2_next_review <= now,
            )
            .order_by(Flashcard.sm2_next_review.asc())
            .limit(limit)
        )
        
        cards = result.scalars().all()
        
        return [
            {
                "id": str(card.id),
                "front": card.front,
                "back": card.back,
                "metadata": card.card_metadata,
                "ease_factor": card.sm2_ease_factor,
                "interval": card.sm2_interval,
                "repetitions": card.sm2_repetitions,
                "next_review": card.sm2_next_review.isoformat(),
                "source": card.source,
            }
            for card in cards
        ]
    
    async def get_review_stats(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Lấy thống kê review của user.
        
        Returns:
            Dict với stats
        """
        from app.models.flashcard import Flashcard, StudySession
        
        # Total cards
        total_cards_result = await db.execute(
            select(func.count(Flashcard.id)).where(Flashcard.user_id == user_id)
        )
        total_cards = total_cards_result.scalar() or 0
        
        # Due cards count
        now = datetime.utcnow()
        due_cards_result = await db.execute(
            select(func.count(Flashcard.id)).where(
                Flashcard.user_id == user_id,
                Flashcard.sm2_next_review <= now,
            )
        )
        due_cards = due_cards_result.scalar() or 0
        
        # Total reviews
        total_reviews_result = await db.execute(
            select(func.count(StudySession.id)).where(
                StudySession.user_id == user_id
            )
        )
        total_reviews = total_reviews_result.scalar() or 0
        
        # Average quality
        avg_quality_result = await db.execute(
            select(func.avg(StudySession.quality)).where(
                StudySession.user_id == user_id
            )
        )
        avg_quality = avg_quality_result.scalar() or 0
        
        # Streak (ngày liên tiếp ôn tập)
        # Đếm số ngày liên tiếp có ít nhất 1 review
        seven_days_ago = now - timedelta(days=7)
        streak_result = await db.execute(
            select(func.count(func.distinct(func.date(StudySession.reviewed_at))))
            .where(
                StudySession.user_id == user_id,
                StudySession.reviewed_at >= seven_days_ago,
            )
        )
        active_days = streak_result.scalar() or 0
        
        return {
            "total_cards": total_cards,
            "due_cards": due_cards,
            "total_reviews": total_reviews,
            "avg_quality": round(avg_quality, 2),
            "streak_7d": active_days,
        }
