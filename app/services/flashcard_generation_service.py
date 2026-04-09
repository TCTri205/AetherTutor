"""
FlashcardGenerationService - Auto-generate flashcards từ graph entities.

Service này tự động tạo flashcards từ knowledge graph entities:
- Entity name → front (câu hỏi)
- Entity description → back (câu trả lời)
- Có thể generate từ document cụ thể hoặc từ quiz wrong answers
"""
from typing import List, Optional, Dict, Any
import uuid
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.flashcard_repo import FlashcardRepository
from ..repositories.graph_repo import GraphRepository
from ..models.flashcard import Flashcard
from ..constants import FLASHCARD_GENERATION_BATCH_SIZE


class FlashcardGenerationService:
    """
    Service tự động generate flashcards từ graph entities.
    """

    def __init__(
        self,
        flashcard_repo: FlashcardRepository,
        graph_repo: GraphRepository
    ):
        self.flashcard_repo = flashcard_repo
        self.graph_repo = graph_repo

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

        Args:
            user_id: User tạo flashcards
            document_id: Document để lấy entities
            source: Source tag cho flashcards
            max_cards: Số lượng tối đa
            min_confidence: Confidence threshold cho entities
            db_session: DB session (optional)

        Returns:
            List of Flashcard đã tạo
        """
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
        db_session: Optional[AsyncSession] = None
    ) -> List[Flashcard]:
        """
        Generate flashcards từ quiz wrong answers.
        (Implement sau khi có Quiz system)
        """
        # TODO: Implement khi có Quiz system
        logger.warning("generate_from_quiz_wrong_answers chưa được implement")
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
    graph_repo: GraphRepository
) -> FlashcardGenerationService:
    """Factory function để tạo FlashcardGenerationService."""
    return FlashcardGenerationService(flashcard_repo, graph_repo)
