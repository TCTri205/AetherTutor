"""
FlashcardGenerationService - Auto-generate flashcards từ graph entities.

Service này tự động tạo flashcards từ knowledge graph entities:
- Entity name → front (câu hỏi)
- Entity description → back (câu trả lời)
- Có thể generate từ document cụ thể hoặc từ quiz wrong answers
"""
from typing import List, Optional, Dict, Any
import uuid
import json
import logging
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.flashcard_repo import FlashcardRepository
from ..repositories.graph_repo import GraphRepository
from ..repositories.quiz_repo import QuizResultRepository
from ..repositories.document_repo import DocumentRepository
from ..models.flashcard import Flashcard
from ..models.document import DocumentStatus
from ..services.llm_service import LLMService


class FlashcardGenerationService:
    """
    Service tự động generate flashcards từ graph entities.
    """

    def __init__(
        self,
        flashcard_repo: FlashcardRepository,
        graph_repo: GraphRepository,
        document_repo: DocumentRepository,
        llm_service: Optional[LLMService] = None,
        quiz_result_repo: Optional[QuizResultRepository] = None,
    ):
        self.flashcard_repo = flashcard_repo
        self.graph_repo = graph_repo
        self.document_repo = document_repo
        self.llm_service = llm_service
        self.quiz_result_repo = quiz_result_repo
        self._logger = logging.getLogger(__name__)

    async def generate_from_document(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        source: str = "auto_generated",
        max_cards: int = 50,
        min_confidence: float = 0.7,
        db_session: Optional[AsyncSession] = None
    ) -> List[Flashcard]:
        """
        Auto-generate flashcards từ entities của một document.

        ⚠️ BR-004: Flashcard chỉ được sinh từ entities/relations đã hoàn thành processing.
        Validate document status PHẢI là COMPLETED trước khi generate.

        Args:
            user_id: User tạo flashcards
            document_id: Document để lấy entities
            source: Source tag cho flashcards
            max_cards: Số lượng tối đa
            min_confidence: Confidence threshold cho entities
            db_session: DB session (optional)

        Returns:
            List of Flashcard đã tạo

        Raises:
            ValueError: Nếu document chưa hoàn thành processing
        """
        # BR-004: Validate document status
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        if doc.status != DocumentStatus.COMPLETED:
            raise ValueError(
                f"Document chưa hoàn thành processing (status: {doc.value}). "
                f"Flashcard chỉ được sinh từ document đã completed (BR-004)."
            )

        # Lấy entities từ document
        entities = await self.graph_repo.get_entities_by_document(
            document_id=document_id,
            min_confidence=min_confidence,
            limit=max_cards
        )

        if not entities:
            logger.info(f"Không tìm thấy entities cho document {document_id}")
            return []

        # Tạo flashcards từ entities
        flashcards = []
        for entity in entities:
            front = f"{entity['name']} là gì?"
            back = entity.get('description', f"Xem tài liệu để biết chi tiết về {entity['name']}")

            flashcard = Flashcard(
                user_id=user_id,
                front=front,
                back=back,
                document_id=document_id,
                source=source,
                metadata={
                    "entity_id": entity.get("id"),
                    "entity_type": entity.get("entity_type", "concept"),
                    "confidence": entity.get("confidence", 0.0),
                    "auto_generated": True
                }
            )
            flashcards.append(flashcard)

        # Bulk insert
        if flashcards:
            created = await self.flashcard_repo.bulk_create(flashcards)
            if db_session:
                await db_session.flush()
            logger.info(f"Đã tạo {len(created)} flashcards từ document {document_id}")
            return created

        return []

    async def generate_from_quiz_wrong_answers(
        self,
        user_id: uuid.UUID,
        quiz_result_id: uuid.UUID,
        db_session: Optional[AsyncSession] = None,
    ) -> List[Flashcard]:
        """
        Generate flashcards từ quiz wrong answers sử dụng LLM.

        Args:
            user_id: User tạo flashcards
            quiz_result_id: Quiz result ID để lấy wrong answers
            db_session: DB session (optional)

        Returns:
            List of Flashcard đã tạo
        """
        if not self.llm_service:
            self._logger.error("LLM service not available for flashcard generation")
            return []

        if not self.quiz_result_repo:
            self._logger.error("QuizResultRepository not available")
            return []

        # Fetch quiz result with answers
        result = await self.quiz_result_repo.get_by_id_with_answers(quiz_result_id)
        if not result:
            self._logger.warning(f"Quiz result {quiz_result_id} not found")
            return []

        if str(result.user_id) != str(user_id):
            self._logger.warning(f"Quiz result {quiz_result_id} does not belong to user {user_id}")
            return []

        # Filter wrong answers
        wrong_answers = [
            {
                "question": a.question_text,
                "correct_answer": a.correct_answer if isinstance(a.correct_answer, str) else str(a.correct_answer),
                "user_answer": a.user_answer if isinstance(a.user_answer, str) else str(a.user_answer),
                "entity_name": a.entity_name or "",
                "explanation": a.explanation or "",
            }
            for a in result.answers
            if not a.is_correct
        ]

        if not wrong_answers:
            self._logger.info(f"No wrong answers in quiz result {quiz_result_id}")
            return []

        # Use LLM to generate flashcards
        wrong_answers_json = json.dumps(wrong_answers, ensure_ascii=False, indent=2)

        prompt = f"""Generate flashcards from these quiz wrong answers to help the user learn:
{wrong_answers_json}

For each wrong answer, create a flashcard with:
- front: The question or concept they got wrong (concise, clear)
- back: The correct answer with a brief explanation
- tags: Relevant topics as a list of strings

Return ONLY a JSON array with no markdown formatting. Each object must have:
- "front": string
- "back": string
- "tags": array of strings

Example:
[{{"front": "What is photosynthesis?", "back": "Photosynthesis is the process by which plants convert sunlight into energy. Correct answer: ...", "tags": ["biology", "plants"]}}]"""

        try:
            response = await self.llm_service.get_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content if response.choices else ""
            if not content:
                self._logger.warning("LLM returned empty response")
                return []

            # Parse JSON from response - handle potential markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code block if present
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else lines[0].replace("```json", "").replace("```", "")

            flashcards_data = json.loads(content)

            if not isinstance(flashcards_data, list):
                self._logger.warning(f"LLM response is not a JSON array, got: {type(flashcards_data)}")
                return []

            # Create Flashcard objects
            flashcards = []
            for fc in flashcards_data:
                front = fc.get("front", "").strip()
                back = fc.get("back", "").strip()

                if not front or not back:
                    continue

                flashcard = Flashcard(
                    user_id=user_id,
                    front=front,
                    back=back,
                    source="quiz_wrong_answer",
                    card_metadata={
                        "quiz_result_id": str(quiz_result_id),
                        "auto_generated": True,
                        "tags": fc.get("tags", []),
                    },
                )
                flashcards.append(flashcard)

            # Bulk insert
            if flashcards:
                created = await self.flashcard_repo.bulk_create(flashcards)
                if db_session:
                    await db_session.flush()
                self._logger.info(
                    f"Created {len(created)} flashcards from quiz result {quiz_result_id}"
                )
                return created

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            self._logger.error(f"Error generating flashcards from quiz: {e}")

        return []

    async def generate_custom(
        self,
        user_id: uuid.UUID,
        entities_data: List[Dict[str, Any]],
        source: str = "manual",
        db_session: Optional[AsyncSession] = None
    ) -> List[Flashcard]:
        """
        Generate flashcards từ danh sách entities tùy chỉnh.

        Args:
            user_id: User ID
            entities_data: List của dicts với keys: name, description, metadata
            source: Source tag
            db_session: DB session

        Returns:
            List of Flashcard đã tạo
        """
        flashcards = []
        for entity in entities_data:
            front = entity.get("front", f"{entity['name']} là gì?")
            back = entity.get("back", entity.get("description", ""))

            flashcard = Flashcard(
                user_id=user_id,
                front=front,
                back=back,
                source=source,
                metadata=entity.get("metadata", {})
            )
            flashcards.append(flashcard)

        if flashcards:
            created = await self.flashcard_repo.bulk_create(flashcards)
            if db_session:
                await db_session.flush()
            logger.info(f"Đã tạo {len(created)} flashcards tùy chỉnh")
            return created

        return []


def get_flashcard_generation_service(
    flashcard_repo: FlashcardRepository,
    graph_repo: GraphRepository,
    document_repo: DocumentRepository,
    llm_service: Optional[LLMService] = None,
    quiz_result_repo: Optional[QuizResultRepository] = None,
) -> FlashcardGenerationService:
    """Factory function để tạo FlashcardGenerationService."""
    return FlashcardGenerationService(
        flashcard_repo, graph_repo, document_repo, llm_service, quiz_result_repo
    )
