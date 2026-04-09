"""
Pydantic schemas for Flashcard and StudySession APIs.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


# --- Flashcard Schemas ---

class FlashcardBase(BaseModel):
    front: str = Field(..., min_length=1, max_length=2000, description="Mặt trước của flashcard")
    back: str = Field(..., min_length=1, max_length=5000, description="Mặt sau của flashcard")
    source: Optional[str] = Field(default="manual", description="Nguồn: manual, quiz_wrong_answer, auto_generated")
    metadata: Optional[dict] = Field(default_factory=dict, description="Metadata bổ sung")


class FlashcardCreate(FlashcardBase):
    """Schema để tạo flashcard mới."""
    document_id: Optional[uuid.UUID] = Field(None, description="Document ID liên kết (nếu có)")


class FlashcardUpdate(BaseModel):
    """Schema để cập nhật flashcard."""
    front: Optional[str] = Field(None, min_length=1, max_length=2000)
    back: Optional[str] = Field(None, min_length=1, max_length=5000)


class FlashcardRead(FlashcardBase):
    """Schema trả về cho client."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    # SM-2 params
    sm2_ease_factor: float
    sm2_interval: int
    sm2_repetitions: int
    sm2_next_review: datetime


class FlashcardDueResponse(BaseModel):
    """Schema trả về cho due cards."""
    cards: List[FlashcardRead]
    total_due: int


# --- Review Schemas ---

class FlashcardReviewRequest(BaseModel):
    """Schema để review một flashcard."""
    card_id: uuid.UUID
    quality: int = Field(..., ge=0, le=5, description="SM-2 quality rating: 0-5 (0=Again, 2=Hard, 3=Good, 5=Easy)")
    idempotency_key: Optional[str] = Field(None, max_length=100, description="Key để tránh duplicate review")
    time_taken_ms: Optional[int] = Field(None, ge=0, description="Thời gian xem card (ms)")


class FlashcardReviewResponse(BaseModel):
    """Schema trả về sau khi review."""
    success: bool
    message: str
    card_id: str
    ease_factor: float
    interval: int
    repetitions: int
    next_review: str


# --- Stats Schemas ---

class FlashcardStatsResponse(BaseModel):
    """Schema trả về thống kê flashcard."""
    total_cards: int
    due_cards: int
    total_reviews: int
    avg_quality: float
    streak_days: int
    total_reviews_7d: int


# --- Bulk Generation Schema ---

class FlashcardBulkGenerateRequest(BaseModel):
    """Schema để auto-generate flashcards."""
    document_id: uuid.UUID
    source: str = Field(default="auto_generated", description="Nguồn generate")


class FlashcardBulkGenerateResponse(BaseModel):
    """Schema trả về sau khi generate."""
    success: bool
    cards_created: int
    cards: List[FlashcardRead]
