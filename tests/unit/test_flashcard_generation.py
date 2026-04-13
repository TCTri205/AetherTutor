"""
Unit tests cho FlashcardGenerationService.

Tests cho:
- generate_from_document: validation BR-004, entity extraction
- generate_from_quiz_wrong_answers: LLM flashcard generation
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.flashcard_generation_service import FlashcardGenerationService
from app.models.document import DocumentStatus


# ============================================================
# Tests cho generate_from_document (BR-004 validation)
# ============================================================

class TestGenerateFromDocument:
    """Tests cho document-based flashcard generation."""

    def _make_service(self):
        """Tạo service với mock repos."""
        flashcard_repo = AsyncMock()
        graph_repo = AsyncMock()
        document_repo = AsyncMock()
        return FlashcardGenerationService(
            flashcard_repo=flashcard_repo,
            graph_repo=graph_repo,
            document_repo=document_repo
        )

    @pytest.mark.asyncio
    async def test_document_not_found(self):
        """Document không tồn tại → raise ValueError."""
        service = self._make_service()
        service.document_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.generate_from_document(
                user_id=uuid.uuid4(),
                document_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_br004_reject_pending_document(self):
        """Document PENDING → raise ValueError (BR-004)."""
        service = self._make_service()
        mock_doc = MagicMock()
        mock_doc.status = DocumentStatus.PENDING
        service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)

        with pytest.raises(ValueError, match="chưa hoàn thành processing"):
            await service.generate_from_document(
                user_id=uuid.uuid4(),
                document_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_br004_reject_processing_document(self):
        """Document PROCESSING → raise ValueError (BR-004)."""
        service = self._make_service()
        mock_doc = MagicMock()
        mock_doc.status = DocumentStatus.PROCESSING
        service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)

        with pytest.raises(ValueError, match="chưa hoàn thành processing"):
            await service.generate_from_document(
                user_id=uuid.uuid4(),
                document_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_br004_reject_failed_document(self):
        """Document FAILED → raise ValueError (BR-004)."""
        service = self._make_service()
        mock_doc = MagicMock()
        mock_doc.status = DocumentStatus.FAILED
        service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)

        with pytest.raises(ValueError, match="chưa hoàn thành processing"):
            await service.generate_from_document(
                user_id=uuid.uuid4(),
                document_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_br004_allows_completed_document(self):
        """Document COMPLETED → cho phép generate."""
        service = self._make_service()
        mock_doc = MagicMock()
        mock_doc.status = DocumentStatus.COMPLETED
        service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)

        # Mock graph repo trả về entities
        service.graph_repo.get_entities_by_document = AsyncMock(return_value=[
            {"id": "ent_1", "name": "Test Entity", "description": "A test entity", "entity_type": "concept", "confidence": 0.9}
        ])

        # Mock flashcard bulk create
        mock_card = MagicMock()
        service.flashcard_repo.bulk_create = AsyncMock(return_value=[mock_card])

        result = await service.generate_from_document(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4()
        )

        assert len(result) == 1
        service.flashcard_repo.bulk_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_entities_returns_empty(self):
        """Document completed nhưng không có entities → return []."""
        service = self._make_service()
        mock_doc = MagicMock()
        mock_doc.status = DocumentStatus.COMPLETED
        service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)
        service.graph_repo.get_entities_by_document = AsyncMock(return_value=[])

        result = await service.generate_from_document(
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4()
        )

        assert result == []
