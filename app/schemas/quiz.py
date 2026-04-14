"""
Quiz Pydantic schemas for Stage 2 - Examiner & Quiz System
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ===== Request Schemas =====

class QuizGenerateRequest(BaseModel):
    """Request to generate a quiz from a document."""
    document_id: Optional[str] = Field(None, description="Document ID to generate from")
    topic: Optional[str] = Field(None, description="Optional topic filter")
    num_questions: int = Field(
        default=10, ge=1, le=50, description="Number of questions (1-50)"
    )
    question_types: List[str] = Field(
        default=["multiple_choice", "true_false"],
        description="Question types: multiple_choice, true_false",
    )
    difficulty: int = Field(
        default=3, ge=1, le=5, description="Difficulty level 1-5"
    )


class QuizSubmitRequest(BaseModel):
    """Request to submit quiz answers."""
    answers: List[Dict[str, str]] = Field(
        ..., description="List of {question_id, answer} objects"
    )

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v):
        if not v:
            raise ValueError("answers cannot be empty")
        for answer in v:
            if "question_id" not in answer or "answer" not in answer:
                raise ValueError("Each answer must have question_id and answer")
        return v


class QuizFeedbackRequest(BaseModel):
    """Request to submit quality feedback for a quiz."""
    quality_rating: int = Field(
        ..., ge=1, le=5, description="Quality rating 1-5 stars"
    )
    quality_feedback: Optional[str] = Field(
        None, max_length=1000, description="Optional feedback text"
    )


# ===== Response Schemas =====

class QuizQuestionResponse(BaseModel):
    """Single quiz question."""
    question_id: str
    order: int
    entity_name: str
    question_text: str
    question_type: str  # multiple_choice | true_false
    difficulty: int
    bloom_level: str
    options: Optional[List[str]] = None
    # Do NOT include correct_answer in response (prevent cheating)


class QuizResponse(BaseModel):
    """Full quiz response with questions."""
    id: str
    user_id: str
    document_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None
    num_questions: int
    question_types: List[str]
    difficulty: int
    questions: List[QuizQuestionResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizAnswerResponse(BaseModel):
    """Single answer result."""
    question_id: str
    question_text: str
    question_type: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None
    entity_name: Optional[str] = None
    bloom_level: str
    difficulty: int


class WeakAreaResponse(BaseModel):
    """Entity that user struggles with."""
    entity_name: str
    entity_type: str
    bloom_level: str


class QuizResultResponse(BaseModel):
    """Quiz result with detailed breakdown."""
    id: str
    quiz_id: str
    score: float
    correct_count: int
    wrong_count: int
    total_questions: int
    results: List[QuizAnswerResponse]
    weak_areas: List[WeakAreaResponse]
    completed_at: datetime

    model_config = {"from_attributes": True}


class QuizStatsResponse(BaseModel):
    """User's quiz statistics."""
    total_quizzes: int
    average_score: float
    total_questions_answered: int
    total_correct: int
    overall_accuracy: float


class WeakAreasResponse(BaseModel):
    """Top weak areas across all quizzes."""
    entity_name: str
    wrong_count: int
    avg_difficulty: float


class QuizListItemResponse(BaseModel):
    """Quiz list item (summary)."""
    id: str
    title: str
    topic: Optional[str] = None
    num_questions: int
    difficulty: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizResultListItemResponse(BaseModel):
    """Quiz result list item (summary)."""
    id: str
    quiz_id: str
    quiz_title: str
    score: float
    correct_answers: int
    total_questions: int
    completed_at: datetime

    model_config = {"from_attributes": True}


# ===== Flashcard Conversion =====

class FlashcardSuggestionResponse(BaseModel):
    """Flashcard suggestion generated from wrong answers."""
    front: str
    back: str
    metadata: Dict[str, Any]
