"""
Flashcard API endpoints for Stage 2 - Spaced Repetition System.

Endpoints:
- GET /api/v1/flashcards/due - Lấy danh sách cards cần ôn
- POST /api/v1/flashcards/review - Review một card (cập nhật SM-2)
- POST /api/v1/flashcards - Tạo flashcard mới
- GET /api/v1/flashcards - List user's flashcards
- GET /api/v1/flashcards/stats - Thống kê review
- POST /api/v1/flashcards/generate - Auto-generate từ document
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from ..database import get_db
from ..api.dependencies import get_current_user_id
from ..repositories.flashcard_repo import FlashcardRepository
from ..repositories.study_session_repo import StudySessionRepository
from ..services.sm2_service import SM2Service
from ..schemas.flashcard import (
    FlashcardCreate,
    FlashcardRead,
    FlashcardUpdate,
    FlashcardDueResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    FlashcardStatsResponse,
    FlashcardBulkGenerateRequest,
    FlashcardBulkGenerateResponse
)
from ..constants import FLASHCARDS_DUE_DEFAULT_LIMIT

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/due", response_model=FlashcardDueResponse)
async def get_due_flashcards(
    limit: int = Query(FLASHCARDS_DUE_DEFAULT_LIMIT, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách flashcards cần ôn tập.
    Cards có `sm2_next_review <= NOW()` sẽ được trả về.
    """
    repo = FlashcardRepository(db)

    cards = await repo.get_due_cards(user_id, limit=limit)
    total_due = await repo.get_due_cards_count(user_id)

    return FlashcardDueResponse(
        cards=[FlashcardRead.model_validate(c) for c in cards],
        total_due=total_due
    )


@router.post("/review", response_model=FlashcardReviewResponse)
async def review_flashcard(
    request: FlashcardReviewRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Review một flashcard và cập nhật SM-2 parameters.

    Quality scale (SM-2):
    - 0: Again (Hoàn toàn không nhớ)
    - 1: Again (Nhớ mang máng)
    - 2: Hard (Nhớ khó khăn)
    - 3: Good (Nhớ được sau gợi ý)
    - 4: Easy (Nhớ dễ)
    - 5: Easy (Nhớ ngay lập tức)
    """
    sm2_service = SM2Service()

    try:
        result = await sm2_service.review_flashcard(
            db=db,
            card_id=request.card_id,
            quality=request.quality,
            user_id=user_id,
            idempotency_key=request.idempotency_key,
            response_time_ms=request.time_taken_ms,
        )

        return FlashcardReviewResponse(
            success=True,
            message=f"Reviewed: quality={result['quality']}, interval={result['interval']}d",
            card_id=result['card_id'],
            ease_factor=result['ease_factor'],
            interval=result['interval'],
            repetitions=result['repetitions'],
            next_review=result['next_review'],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("", response_model=FlashcardRead, status_code=201)
async def create_flashcard(
    request: FlashcardCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo flashcard mới (manual).
    """
    repo = FlashcardRepository(db)

    card = await repo.create(
        user_id=user_id,
        front=request.front,
        back=request.back,
        document_id=request.document_id,
        source=request.source,
        metadata=request.metadata
    )
    await db.commit()

    return FlashcardRead.model_validate(card)


@router.get("", response_model=List[FlashcardRead])
async def list_flashcards(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source: Optional[str] = Query(None, description="Filter by source: manual, quiz_wrong_answer, auto_generated"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List flashcards của user với pagination.
    """
    repo = FlashcardRepository(db)

    cards = await repo.get_by_user(user_id, skip=skip, limit=limit, source=source)
    return [FlashcardRead.model_validate(c) for c in cards]


@router.get("/stats", response_model=FlashcardStatsResponse)
async def get_flashcard_stats(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thống kê học tập: total cards, due cards, reviews, streak.
    """
    flashcard_repo = FlashcardRepository(db)
    session_repo = StudySessionRepository(db)

    total_cards = await flashcard_repo.count_by_user(user_id)
    due_cards = await flashcard_repo.get_due_cards_count(user_id)
    stats = await session_repo.get_stats(user_id, days=7)

    return FlashcardStatsResponse(
        total_cards=total_cards,
        due_cards=due_cards,
        total_reviews=stats["total_reviews"],
        avg_quality=stats["avg_quality"],
        streak_days=stats["streak_days"],
        total_reviews_7d=stats["total_reviews"]
    )


@router.get("/{card_id}", response_model=FlashcardRead)
async def get_flashcard(
    card_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy chi tiết một flashcard.
    """
    repo = FlashcardRepository(db)

    card = await repo.get_by_id(card_id)
    if not card or card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    return FlashcardRead.model_validate(card)


@router.patch("/{card_id}", response_model=FlashcardRead)
async def update_flashcard(
    card_id: uuid.UUID,
    request: FlashcardUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật flashcard (front/back).
    """
    repo = FlashcardRepository(db)

    card = await repo.get_by_id(card_id)
    if not card or card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    if request.front is not None:
        card.front = request.front
    if request.back is not None:
        card.back = request.back

    await db.commit()
    await db.refresh(card)

    return FlashcardRead.model_validate(card)


@router.delete("/{card_id}", status_code=204)
async def delete_flashcard(
    card_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa flashcard.
    """
    repo = FlashcardRepository(db)

    success = await repo.delete_by_user(user_id, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    await db.commit()


@router.post("/generate", response_model=FlashcardBulkGenerateResponse)
async def generate_flashcards_from_document(
    request: FlashcardBulkGenerateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-generate flashcards từ graph entities trong document.
    """
    from ..repositories.graph_repo import GraphRepository
    from ..services.flashcard_generation_service import FlashcardGenerationService

    flashcard_repo = FlashcardRepository(db)
    graph_repo = GraphRepository(db)

    generation_service = FlashcardGenerationService(
        flashcard_repo=flashcard_repo,
        graph_repo=graph_repo
    )

    cards = await generation_service.generate_from_document(
        user_id=user_id,
        document_id=request.document_id,
        source=request.source,
        max_cards=50,
        min_confidence=0.7,
        db_session=db
    )

    await db.commit()

    return FlashcardBulkGenerateResponse(
        success=True,
        cards_created=len(cards),
        cards=[FlashcardRead.model_validate(c) for c in cards]
    )
