"""
Unit tests cho SM-2 Algorithm (SM2Service).

Test coverage:
- calculate_sm2_update: quality 0-5, first review, reset, overflow
- Edge cases: min ease factor, interval growth
- get_due_cards, get_review_stats
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.sm2_service import SM2Service
from app.constants import SM2_INITIAL_EASE, SM2_MIN_EASE


# ============================================================
# Tests cho calculate_sm2_update (static method)
# ============================================================

class TestCalculateSM2Update:
    """Test thuật toán SM-2 core logic."""

    def test_first_review_perfect_quality(self):
        """Quality=5, first review → interval=1, repetitions=1."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=0,
            current_repetitions=0,
            quality=5,
        )

        assert result["repetitions"] == 1
        assert result["interval"] == 1
        assert result["ease_factor"] == 2.60  # 2.5 + (0.1 - 0 * 0.08)
        assert isinstance(result["next_review"], datetime)
        # next_review nên là ngày mai
        assert result["next_review"] > datetime.utcnow()

    def test_second_review_perfect_quality(self):
        """Quality=5, second review → interval=6, repetitions=2."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=5,
        )

        assert result["repetitions"] == 2
        assert result["interval"] == 6

    def test_third_review_perfect_quality(self):
        """Quality=5, third review → interval = prev * ease (rounded)."""
        result = SM2Service.calculate_sm2_update(
            current_ease=2.60,
            current_interval=6,
            current_repetitions=2,
            quality=5,
        )

        assert result["repetitions"] == 3
        # interval = 6 * 2.60 = 15.6 → round = 16
        assert result["interval"] == 16
        assert result["ease_factor"] == 2.70  # 2.60 + (0.1 - 0 * 0.08)

    def test_quality_0_complete_blackout(self):
        """Quality=0 → reset repetitions, interval=0 (review immediately)."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=10,
            current_repetitions=5,
            quality=0,
        )

        assert result["repetitions"] == 0
        assert result["interval"] == 0  # CR-001: review ngay lập tức
        # Ease factor giảm
        # new_ease = 2.5 + (0.1 - 5 * (0.08 + 5 * 0.02))
        #          = 2.5 + (0.1 - 5 * 0.18)
        #          = 2.5 + (0.1 - 0.9)
        #          = 2.5 - 0.8 = 1.7
        assert result["ease_factor"] == 1.70

    def test_quality_1_incorrect_response(self):
        """Quality=1 → reset, ease factor giảm."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=6,
            current_repetitions=2,
            quality=1,
        )

        assert result["repetitions"] == 0
        assert result["interval"] == 0  # CR-001: review ngay lập tức
        # new_ease = 2.5 + (0.1 - 4 * (0.08 + 4 * 0.02))
        #          = 2.5 + (0.1 - 4 * 0.16)
        #          = 2.5 + (0.1 - 0.64)
        #          = 2.5 - 0.54 = 1.96
        assert result["ease_factor"] == 1.96

    def test_quality_2_correct_but_hard(self):
        """Quality=2 → reset (vì < 3), ease factor giảm nhẹ."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=3,
            current_repetitions=3,
            quality=2,
        )

        assert result["repetitions"] == 0
        assert result["interval"] == 0  # CR-001 fix: review ngay lập tức (interval = 0)
        # new_ease = 2.5 + (0.1 - 3 * (0.08 + 3 * 0.02))
        #          = 2.5 + (0.1 - 3 * 0.14)
        #          = 2.5 + (0.1 - 0.42)
        #          = 2.5 - 0.32 = 2.18
        assert result["ease_factor"] == 2.18

    def test_quality_3_correct_response(self):
        """Quality=3 → success, interval tăng."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=6,
            current_repetitions=2,
            quality=3,
        )

        assert result["repetitions"] == 3
        assert result["interval"] > 6  # interval = 6 * 2.58 = 15
        # new_ease = 2.5 + (0.1 - 2 * (0.08 + 2 * 0.02))
        #          = 2.5 + (0.1 - 2 * 0.12)
        #          = 2.5 + (0.1 - 0.24)
        #          = 2.5 - 0.14 = 2.36
        assert result["ease_factor"] == 2.36

    def test_quality_4_hesitated(self):
        """Quality=4 → success, ease tăng nhẹ."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=4,
        )

        assert result["repetitions"] == 2
        assert result["interval"] == 6  # repetitions == 2 → interval = 6
        # new_ease = 2.5 + (0.1 - 1 * (0.08 + 1 * 0.02))
        #          = 2.5 + (0.1 - 0.10)
        #          = 2.5
        assert result["ease_factor"] == 2.50

    def test_quality_5_perfect(self):
        """Quality=5 → success, ease tăng mạnh nhất."""
        result = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=0,
            quality=5,
        )

        assert result["repetitions"] == 1
        assert result["interval"] == 1
        assert result["ease_factor"] == 2.60

    def test_ease_factor_minimum_boundary(self):
        """Ease factor không được nhỏ hơn SM2_MIN_EASE (1.3)."""
        # Quality=0 nhiều lần sẽ đẩy ease factor xuống rất thấp
        # Test lần 1: ease từ 1.4 → ~0.6 → phải clamp về 1.3
        result = SM2Service.calculate_sm2_update(
            current_ease=1.4,
            current_interval=10,
            current_repetitions=5,
            quality=0,
        )

        assert result["ease_factor"] >= SM2_MIN_EASE
        assert result["repetitions"] == 0

    def test_ease_factor_growth_over_multiple_reviews(self):
        """Ease factor tăng dần khi quality cao liên tiếp."""
        ease = SM2_INITIAL_EASE
        interval = 0
        reps = 0

        # 5 lần review với quality=5
        for _ in range(5):
            result = SM2Service.calculate_sm2_update(
                current_ease=ease,
                current_interval=interval,
                current_repetitions=reps,
                quality=5,
            )
            ease = result["ease_factor"]
            interval = result["interval"]
            reps = result["repetitions"]

        assert reps == 5
        assert ease > SM2_INITIAL_EASE  # ease factor phải tăng
        assert interval > 1  # interval phải tăng

    def test_quality_clamping_negative_to_zero(self):
        """Quality âm phải được clamp về 0."""
        result_neg = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=-1,
        )
        result_zero = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=0,
        )

        # Cả hai phải cho kết quả giống nhau
        assert result_neg == result_zero

    def test_quality_clamping_above_five(self):
        """Quality > 5 phải được clamp về 5."""
        result_six = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=6,
        )
        result_five = SM2Service.calculate_sm2_update(
            current_ease=SM2_INITIAL_EASE,
            current_interval=1,
            current_repetitions=1,
            quality=5,
        )

        assert result_six == result_five

    def test_interval_growth_is_multiplicative(self):
        """Interval tăng theo cấp số nhân khi repetitions > 1."""
        ease = 2.5
        interval = 6
        reps = 2

        intervals = []
        for _ in range(10):
            result = SM2Service.calculate_sm2_update(
                current_ease=ease,
                current_interval=interval,
                current_repetitions=reps,
                quality=4,  # quality ổn định
            )
            intervals.append(result["interval"])
            ease = result["ease_factor"]
            interval = result["interval"]
            reps = result["repetitions"]

        # Interval phải tăng dần (multiplicative growth)
        for i in range(1, len(intervals)):
            assert intervals[i] >= intervals[i - 1]


# ============================================================
# Tests cho review_flashcard (async method)
# ============================================================

class TestReviewFlashcard:

    @pytest.mark.asyncio
    async def test_review_success(self):
        """Review thành công → cập nhật SM-2, tạo StudySession."""
        # Mock dependencies
        from app.models.flashcard import Flashcard

        # Tạo mock card
        mock_card = MagicMock(spec=Flashcard)
        mock_card.id = uuid.uuid4()
        mock_card.user_id = uuid.uuid4()
        mock_card.sm2_ease_factor = SM2_INITIAL_EASE
        mock_card.sm2_interval = 1
        mock_card.sm2_repetitions = 0
        mock_card.sm2_next_review = datetime.utcnow()

        # Mock db session
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_card)
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()  # db.add() is sync in SQLAlchemy

        service = SM2Service()
        result = await service.review_flashcard(
            db=mock_db,
            card_id=mock_card.id,
            quality=5,
            user_id=mock_card.user_id,
        )

        # Verify
        assert result["quality"] == 5
        assert result["repetitions"] == 1
        assert result["interval"] == 1
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_review_card_not_found(self):
        """Card không tồn tại → raise ValueError."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        service = SM2Service()

        with pytest.raises(ValueError, match="không tồn tại hoặc không thuộc về bạn"):
            await service.review_flashcard(
                db=mock_db,
                card_id=uuid.uuid4(),
                quality=5,
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_review_wrong_user(self):
        """Card không thuộc về user → raise ValueError."""
        from app.models.flashcard import Flashcard

        mock_card = MagicMock(spec=Flashcard)
        mock_card.id = uuid.uuid4()
        mock_card.user_id = uuid.uuid4()  # Different user

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Ownership check fails
        mock_db.execute.return_value = mock_result

        service = SM2Service()

        with pytest.raises(ValueError, match="không tồn tại hoặc không thuộc về bạn"):
            await service.review_flashcard(
                db=mock_db,
                card_id=mock_card.id,
                quality=5,
                user_id=uuid.uuid4(),  # Different user
            )


# ============================================================
# Tests cho get_due_cards (async method)
# ============================================================

class TestGetDueCards:

    @pytest.mark.asyncio
    async def test_get_due_cards_empty(self):
        """Không có cards due → trả về list rỗng."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = SM2Service()
        cards = await service.get_due_cards(
            db=mock_db,
            user_id=uuid.uuid4(),
            limit=50,
        )

        assert cards == []

    @pytest.mark.asyncio
    async def test_get_due_cards_returns_cards(self):
        """Có cards due → trả về list với đúng format."""
        from app.models.flashcard import Flashcard

        now = datetime.utcnow()
        mock_card = MagicMock(spec=Flashcard)
        mock_card.id = uuid.uuid4()
        mock_card.front = "What is AI?"
        mock_card.back = "Artificial Intelligence"
        mock_card.metadata = {"source": "test"}
        mock_card.sm2_ease_factor = 2.5
        mock_card.sm2_interval = 1
        mock_card.sm2_repetitions = 0
        mock_card.sm2_next_review = now - timedelta(days=1)  # Due
        mock_card.source = "auto"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_card]
        mock_db.execute.return_value = mock_result

        service = SM2Service()
        cards = await service.get_due_cards(
            db=mock_db,
            user_id=uuid.uuid4(),
            limit=50,
        )

        assert len(cards) == 1
        assert cards[0]["front"] == "What is AI?"
        assert cards[0]["back"] == "Artificial Intelligence"
        assert cards[0]["ease_factor"] == 2.5
        assert cards[0]["interval"] == 1


# ============================================================
# Tests cho get_review_stats (async method)
# ============================================================

class TestGetReviewStats:

    @pytest.mark.asyncio
    async def test_stats_empty_user(self):
        """User không có data → stats = 0."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        service = SM2Service()
        stats = await service.get_review_stats(
            db=mock_db,
            user_id=uuid.uuid4(),
        )

        assert stats["total_cards"] == 0
        assert stats["due_cards"] == 0
        assert stats["total_reviews"] == 0
        assert stats["avg_quality"] == 0
        assert stats["streak_7d"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_data(self):
        """User có data → stats đúng."""
        mock_db = AsyncMock()
        # Mock các query khác nhau
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=10)),  # total_cards
            MagicMock(scalar=MagicMock(return_value=5)),   # due_cards
            MagicMock(scalar=MagicMock(return_value=50)),  # total_reviews
            MagicMock(scalar=MagicMock(return_value=4.2)), # avg_quality
            MagicMock(scalar=MagicMock(return_value=3)),   # streak
        ]

        service = SM2Service()
        stats = await service.get_review_stats(
            db=mock_db,
            user_id=uuid.uuid4(),
        )

        assert stats["total_cards"] == 10
        assert stats["due_cards"] == 5
        assert stats["total_reviews"] == 50
        assert stats["avg_quality"] == 4.2
        assert stats["streak_7d"] == 3
