"""
QuizAnalysisService - Analyze quiz results and generate study recommendations.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.repositories.quiz_repo import QuizResultRepository
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class QuizAnalysisService:
    """
    Service for analyzing quiz results and generating personalized study recommendations.
    """

    def __init__(self, quiz_result_repo: QuizResultRepository):
        self.quiz_result_repo = quiz_result_repo

    async def analyze_weak_areas(
        self,
        quiz_result_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Analyze a specific quiz result to identify weak areas.
        
        Returns:
            Dict with:
            - weak_entities: List of entities user got wrong
            - bloom_level_breakdown: Performance by Bloom's taxonomy level
            - difficulty_analysis: Performance by difficulty level
            - recommendations: AI-generated study tips
        """
        result = await self.quiz_result_repo.get_by_id_with_answers(quiz_result_id)
        if not result:
            raise ValueError(f"Quiz result {quiz_result_id} not found")

        answers = result.answers
        if not answers:
            return {
                "quiz_result_id": str(quiz_result_id),
                "weak_entities": [],
                "bloom_level_breakdown": {},
                "difficulty_analysis": {},
                "recommendations": [],
            }

        # Analyze wrong answers
        weak_entities = []
        bloom_stats = {}
        difficulty_stats = {}

        for answer in answers:
            entity_name = answer.entity_name
            bloom_level = getattr(answer, "bloom_level", "remember")
            difficulty = answer.difficulty

            # Track bloom level performance
            if bloom_level not in bloom_stats:
                bloom_stats[bloom_level] = {"total": 0, "correct": 0}
            bloom_stats[bloom_level]["total"] += 1
            if answer.is_correct:
                bloom_stats[bloom_level]["correct"] += 1

            # Track difficulty performance
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {"total": 0, "correct": 0}
            difficulty_stats[difficulty]["total"] += 1
            if answer.is_correct:
                difficulty_stats[difficulty]["correct"] += 1

            # Collect weak entities
            if not answer.is_correct and entity_name:
                weak_entities.append({
                    "entity_name": entity_name,
                    "question_text": answer.question_text,
                    "correct_answer": answer.correct_answer,
                    "difficulty": difficulty,
                })

        # Calculate accuracy rates
        for level, stats in bloom_stats.items():
            stats["accuracy"] = (
                round(stats["correct"] / stats["total"] * 100, 2)
                if stats["total"] > 0
                else 0
            )

        for diff, stats in difficulty_stats.items():
            stats["accuracy"] = (
                round(stats["correct"] / stats["total"] * 100, 2)
                if stats["total"] > 0
                else 0
            )

        # Generate AI recommendations
        recommendations = await self._generate_recommendations(
            weak_entities=weak_entities,
            bloom_stats=bloom_stats,
            difficulty_stats=difficulty_stats,
            score=result.score,
        )

        return {
            "quiz_result_id": str(quiz_result_id),
            "weak_entities": weak_entities[:10],  # Top 10
            "bloom_level_breakdown": bloom_stats,
            "difficulty_analysis": difficulty_stats,
            "recommendations": recommendations,
        }

    async def generate_study_recommendation(
        self,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Generate personalized study recommendations based on user's quiz history.
        
        Returns:
            Dict with:
            - topics_to_review: List of topics/entities to focus on
            - suggested_difficulty: Recommended difficulty level for next quiz
            - study_plan: AI-generated study plan
            - estimated_time: Suggested study time (minutes)
        """
        # Get user's quiz stats
        stats = await self.quiz_result_repo.get_stats(user_id)
        
        if stats["total_quizzes"] == 0:
            return {
                "topics_to_review": [],
                "suggested_difficulty": 2,
                "study_plan": "Bắt đầu với quiz đầu tiên để AI có thể phân tích và gợi ý!",
                "estimated_time_minutes": 15,
            }

        # Get weak areas across all quizzes
        weak_areas = await self.quiz_result_repo.get_weak_areas(user_id, limit=15)

        # Identify patterns
        low_accuracy_bloom = []
        for bloom_level, bloom_data in (
            await self._get_user_bloom_breakdown(user_id)
        ).items():
            if bloom_data.get("accuracy", 100) < 70:
                low_accuracy_bloom.append(bloom_level)

        # Generate AI study plan
        study_plan = await self._generate_study_plan(
            weak_areas=weak_areas,
            low_accuracy_bloom=low_accuracy_bloom,
            overall_accuracy=stats["overall_accuracy"],
        )

        # Suggest next difficulty
        if stats["overall_accuracy"] >= 80:
            suggested_difficulty = min(5, 4)  # Move up
        elif stats["overall_accuracy"] >= 60:
            suggested_difficulty = 3  # Stay
        else:
            suggested_difficulty = max(1, 2)  # Move down

        # Estimate study time based on weak areas
        estimated_time = max(15, len(weak_areas) * 5)  # 5 min per weak area

        return {
            "topics_to_review": [w["entity_name"] for w in weak_areas[:10]],
            "suggested_difficulty": suggested_difficulty,
            "study_plan": study_plan,
            "estimated_time_minutes": estimated_time,
            "overall_accuracy": stats["overall_accuracy"],
            "total_quizzes_taken": stats["total_quizzes"],
        }

    # ========== Private Methods ==========

    async def _generate_recommendations(
        self,
        weak_entities: List[Dict],
        bloom_stats: Dict,
        difficulty_stats: Dict,
        score: float,
    ) -> List[str]:
        """Generate AI-powered study recommendations."""
        if not weak_entities:
            return ["Xuất sắc! Bạn đã trả lời đúng tất cả câu hỏi."]

        # Identify weakest bloom level
        weakest_bloom = min(
            bloom_stats.items(),
            key=lambda x: x[1].get("accuracy", 100),
            default=None,
        )

        prompt = f"""Dựa trên kết quả quiz với điểm số {score:.1f}%, hãy đưa ra lời khuyên học tập:

Các entity sai: {', '.join([e['entity_name'] for e in weak_entities[:5]])}
Mức Bloom yếu nhất: {weakest_bloom[0] if weakest_bloom else 'N/A'} (accuracy: {weakest_bloom[1].get('accuracy', 0):.1f}% nếu weakest_bloom else 'N/A')

Đưa ra 3-5 lời khuyên cụ thể, ngắn gọn (mỗi lời 1-2 câu) để cải thiện.
Trả về JSON array: ["Lời khuyên 1", "Lời khuyên 2", ...]
"""

        try:
            from pydantic import BaseModel
            from typing import List as TypingList

            class RecommendationResponse(BaseModel):
                recommendations: TypingList[str]

            response = await llm_service.structured_extraction(
                prompt=prompt,
                response_model=RecommendationResponse,
                max_retries=2,
            )

            if response and response.recommendations:
                return response.recommendations
        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")

        # Fallback recommendations
        fallback = [
            f"Ôn tập các khái niệm: {', '.join([e['entity_name'] for e in weak_entities[:3]])}",
            "Làm lại quiz với chế độ xem giải thích chi tiết",
            "Tạo flashcards từ các câu sai để ôn tập hàng ngày",
        ]
        return fallback

    async def _generate_study_plan(
        self,
        weak_areas: List[Dict],
        low_accuracy_bloom: List[str],
        overall_accuracy: float,
    ) -> str:
        """Generate personalized study plan using LLM."""
        weak_topics = ", ".join([w["entity_name"] for w in weak_areas[:5]])
        bloom_issues = ", ".join(low_accuracy_bloom) if low_accuracy_bloom else "Không có"

        prompt = f"""Học viên có độ chính xác tổng thể {overall_accuracy:.1f}%.

Các chủ đề yếu: {weak_topics}
Mức Bloom gặp khó khăn: {bloom_issues}

Viết kế hoạch học tập ngắn gọn (3-4 câu) bằng tiếng Việt, bao gồm:
1. Chủ đề nào nên ôn trước
2. Phương pháp học gợi ý (đọc lại, làm quiz, tạo flashcards, v.v.)
3. Thời gian ước tích mỗi ngày

Trả về JSON: {{"study_plan": "Nội dung kế hoạch"}}
"""

        try:
            from pydantic import BaseModel

            class StudyPlanResponse(BaseModel):
                study_plan: str

            response = await llm_service.structured_extraction(
                prompt=prompt,
                response_model=StudyPlanResponse,
                max_retries=2,
            )

            if response and response.study_plan:
                return response.study_plan
        except Exception as e:
            logger.warning(f"Failed to generate study plan: {e}")

        return f"Ôn tập {len(weak_areas)} chủ đề yếu, tập trung vào các mức Bloom: {bloom_issues}. Làm quiz và flashcards hàng ngày."

    async def _get_user_bloom_breakdown(
        self,
        user_id: uuid.UUID,
    ) -> Dict[str, Dict[str, Any]]:
        """Get user's performance breakdown by Bloom's taxonomy level."""
        # This would ideally query across all quiz results
        # For now, return empty dict (will be populated when we have data)
        return {}
