"""
Quiz repositories for Stage 2 - Examiner & Quiz System
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.models.quiz import Quiz, QuizResult, QuizAnswer
from .base import BaseRepository


class QuizRepository(BaseRepository[Quiz]):
    """Repository for Quiz model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Quiz)

    async def create_quiz(
        self,
        user_id: uuid.UUID,
        title: str,
        questions: List[Dict[str, Any]],
        document_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        topic: Optional[str] = None,
        question_types: Optional[List[str]] = None,
        difficulty: int = 3,
        metadata: Optional[Dict] = None,
    ) -> Quiz:
        """Create a new quiz with questions stored in metadata."""
        quiz = Quiz(
            user_id=user_id,
            document_id=document_id,
            title=title,
            description=description,
            topic=topic,
            num_questions=len(questions),
            question_types=question_types or ["multiple_choice"],
            difficulty=difficulty,
            metadata={
                "questions": questions,
                **(metadata or {}),
            },
        )
        self.session.add(quiz)
        await self.session.flush()
        return quiz

    async def get_by_id_with_questions(self, quiz_id: uuid.UUID) -> Optional[Quiz]:
        """Get quiz by ID."""
        stmt = select(Quiz).where(Quiz.id == quiz_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        document_id: Optional[uuid.UUID] = None,
    ) -> List[Quiz]:
        """Get quizzes by user with optional document filter."""
        stmt = select(Quiz).where(Quiz.user_id == user_id)
        if document_id:
            stmt = stmt.where(Quiz.document_id == document_id)
        stmt = stmt.order_by(desc(Quiz.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Count quizzes by user."""
        stmt = select(func.count()).select_from(Quiz).where(Quiz.user_id == user_id)
        if document_id:
            stmt = stmt.where(Quiz.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()


class QuizResultRepository(BaseRepository[QuizResult]):
    """Repository for QuizResult model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, QuizResult)

    async def create_result(
        self,
        user_id: uuid.UUID,
        quiz_id: uuid.UUID,
        score: float,
        total_questions: int,
        correct_answers: int,
        weak_areas: Optional[List[Dict]] = None,
    ) -> QuizResult:
        """Create a quiz result record."""
        result = QuizResult(
            user_id=user_id,
            quiz_id=quiz_id,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            weak_areas=weak_areas or [],
        )
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_by_id_with_answers(self, result_id: uuid.UUID) -> Optional[QuizResult]:
        """Get quiz result with all answers."""
        stmt = (
            select(QuizResult)
            .where(QuizResult.id == result_id)
            .options(selectinload(QuizResult.answers))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        quiz_id: Optional[uuid.UUID] = None,
    ) -> List[QuizResult]:
        """Get quiz results by user."""
        stmt = (
            select(QuizResult)
            .where(QuizResult.user_id == user_id)
            .options(selectinload(QuizResult.quiz))
        )
        if quiz_id:
            stmt = stmt.where(QuizResult.quiz_id == quiz_id)
        stmt = stmt.order_by(desc(QuizResult.completed_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's quiz statistics."""
        # Total quizzes taken
        total_stmt = select(func.count()).select_from(QuizResult).where(
            QuizResult.user_id == user_id
        )
        total_result = await self.session.execute(total_stmt)
        total_quizzes = total_result.scalar_one()

        if total_quizzes == 0:
            return {
                "total_quizzes": 0,
                "average_score": 0.0,
                "total_questions_answered": 0,
                "total_correct": 0,
                "overall_accuracy": 0.0,
            }

        # Average score
        avg_stmt = select(func.avg(QuizResult.score)).where(
            QuizResult.user_id == user_id
        )
        avg_result = await self.session.execute(avg_stmt)
        average_score = avg_result.scalar_one() or 0.0

        # Total questions
        questions_stmt = select(
            func.sum(QuizResult.total_questions),
            func.sum(QuizResult.correct_answers),
        ).where(QuizResult.user_id == user_id)
        questions_result = await self.session.execute(questions_stmt)
        row = questions_result.first()
        total_questions = row[0] or 0
        total_correct = row[1] or 0

        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0

        return {
            "total_quizzes": total_quizzes,
            "average_score": round(float(average_score), 2),
            "total_questions_answered": total_questions,
            "total_correct": total_correct,
            "overall_accuracy": round(overall_accuracy, 2),
        }

    async def get_weak_areas(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get entities that user struggles with most across all quiz results.
        Returns list of dicts with entity_name, wrong_count, avg_difficulty.
        """
        # Get all quiz results for user
        stmt = select(QuizResult).where(QuizResult.user_id == user_id)
        result = await self.session.execute(stmt)
        quiz_results = result.scalars().all()

        if not quiz_results:
            return []

        result_ids = [r.id for r in quiz_results]

        # Get all wrong answers grouped by entity
        wrong_stmt = (
            select(
                QuizAnswer.entity_name,
                func.count().label("wrong_count"),
                func.avg(QuizAnswer.difficulty).label("avg_difficulty"),
            )
            .where(
                QuizAnswer.quiz_result_id.in_(result_ids),
                QuizAnswer.is_correct == False,
                QuizAnswer.entity_name.isnot(None),
            )
            .group_by(QuizAnswer.entity_name)
            .order_by(desc("wrong_count"))
            .limit(limit)
        )
        wrong_result = await self.session.execute(wrong_stmt)
        rows = wrong_result.all()

        return [
            {
                "entity_name": row.entity_name,
                "wrong_count": row.wrong_count,
                "avg_difficulty": round(float(row.avg_difficulty), 2),
            }
            for row in rows
        ]

    async def update_quality_feedback(
        self,
        result_id: uuid.UUID,
        quality_rating: int,
        quality_feedback: Optional[str] = None,
    ) -> Optional[QuizResult]:
        """Update quality rating and feedback for a quiz result."""
        stmt = select(QuizResult).where(QuizResult.id == result_id)
        result = await self.session.execute(stmt)
        quiz_result = result.scalars().first()

        if quiz_result:
            quiz_result.quality_rating = quality_rating
            if quality_feedback:
                quiz_result.quality_feedback = quality_feedback
            await self.session.flush()

        return quiz_result

    async def update_feedback_analysis(
        self,
        result_id: uuid.UUID,
        feedback_category: Optional[str] = None,
        feedback_severity: Optional[str] = None,
        feedback_suggestion: Optional[str] = None,
    ) -> Optional[QuizResult]:
        """Update feedback analysis results for a quiz result."""
        stmt = select(QuizResult).where(QuizResult.id == result_id)
        result = await self.session.execute(stmt)
        quiz_result = result.scalars().first()

        if quiz_result:
            if feedback_category is not None:
                quiz_result.feedback_category = feedback_category
            if feedback_severity is not None:
                quiz_result.feedback_severity = feedback_severity
            if feedback_suggestion is not None:
                quiz_result.feedback_suggestion = feedback_suggestion
            await self.session.flush()

        return quiz_result


class QuizAnswerRepository(BaseRepository[QuizAnswer]):
    """Repository for QuizAnswer model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, QuizAnswer)

    async def bulk_create_answers(
        self,
        answers: List[QuizAnswer],
    ) -> List[QuizAnswer]:
        """Bulk create quiz answers."""
        self.session.add_all(answers)
        await self.session.flush()
        return answers

    async def get_by_result_id(self, quiz_result_id: uuid.UUID) -> List[QuizAnswer]:
        """Get all answers for a quiz result."""
        stmt = (
            select(QuizAnswer)
            .where(QuizAnswer.quiz_result_id == quiz_result_id)
            .order_by(QuizAnswer.question_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
