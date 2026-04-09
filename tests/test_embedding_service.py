"""
Unit tests cho EmbeddingService.

Test cases:
1. OpenAI provider initialization
2. Ollama provider initialization
3. Single embedding generation
4. Batch embedding generation
5. Empty text handling
6. Health check
7. Fallback khi provider không available
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.embedding_service import EmbeddingService
from app.constants import EMBEDDING_DIM_OPENAI, EMBEDDING_DIM_OLLAMA


class TestEmbeddingServiceInitialization:
    """Test initialization với các provider khác nhau."""

    @patch("app.services.embedding_service.settings")
    def test_openai_provider_initialization(self, mock_settings):
        """OpenAI provider được khởi tạo đúng khi config là 'openai'."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-valid-key"

        service = EmbeddingService()

        assert service.provider == "openai"
        assert service.dimension == EMBEDDING_DIM_OPENAI
        assert service.is_cloud is True
        assert service.is_local is False
        assert service._openai_client is not None

    @patch("app.services.embedding_service.settings")
    def test_ollama_provider_initialization(self, mock_settings):
        """Ollama provider được khởi tạo đúng khi config là 'ollama'."""
        mock_settings.EMBEDDING_PROVIDER = "ollama"
        mock_settings.OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
        mock_settings.OLLAMA_EMBEDDING_URL = "http://localhost:11434"

        service = EmbeddingService()

        assert service.provider == "ollama"
        assert service.dimension == EMBEDDING_DIM_OLLAMA
        assert service.is_local is True
        assert service.is_cloud is False
        assert service._ollama_client is not None

    @patch("app.services.embedding_service.settings")
    def test_fallback_to_ollama_when_openai_key_invalid(self, mock_settings):
        """Tự động fallback sang Ollama nếu OpenAI API key không hợp lệ."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "your_placeholder_key"  # Invalid key
        mock_settings.OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
        mock_settings.OLLAMA_EMBEDDING_URL = "http://localhost:11434"

        service = EmbeddingService()

        assert service.provider == "ollama"  # Fallback
        assert service._ollama_client is not None


class TestEmbeddingGeneration:
    """Test tạo embeddings."""

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_generate_single_embedding_openai(self, mock_settings):
        """Test tạo embedding đơn với OpenAI."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * EMBEDDING_DIM_OPENAI)]

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedding = await service.generate_embedding("test text")

        assert len(embedding) == EMBEDDING_DIM_OPENAI
        assert embedding[0] == 0.1
        service._openai_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_generate_single_embedding_ollama(self, mock_settings):
        """Test tạo embedding đơn với Ollama."""
        mock_settings.EMBEDDING_PROVIDER = "ollama"
        mock_settings.OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
        mock_settings.OLLAMA_EMBEDDING_URL = "http://localhost:11434"

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.2] * EMBEDDING_DIM_OLLAMA)]

        service = EmbeddingService()
        service._ollama_client = MagicMock()
        service._ollama_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedding = await service.generate_embedding("test text")

        assert len(embedding) == EMBEDDING_DIM_OLLAMA
        assert embedding[0] == 0.2

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_generate_empty_text_returns_zeros(self, mock_settings):
        """Text rỗng trả về zero vector."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

        service = EmbeddingService()
        embedding = await service.generate_embedding("")

        assert len(embedding) == EMBEDDING_DIM_OPENAI
        assert all(v == 0.0 for v in embedding)

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_generate_batch_embeddings(self, mock_settings):
        """Test batch embedding generation."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * EMBEDDING_DIM_OPENAI),
            MagicMock(embedding=[0.2] * EMBEDDING_DIM_OPENAI),
            MagicMock(embedding=[0.3] * EMBEDDING_DIM_OPENAI),
        ]

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["text1", "text2", "text3"]
        embeddings = await service.generate_embeddings(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == EMBEDDING_DIM_OPENAI for emb in embeddings)

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_generate_batch_with_empty_texts(self, mock_settings):
        """Batch có chứa text rỗng được xử lý đúng."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.5] * EMBEDDING_DIM_OPENAI),
            MagicMock(embedding=[0.6] * EMBEDDING_DIM_OPENAI),
        ]

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["valid text", "", "  ", "another valid"]
        embeddings = await service.generate_embeddings(texts)

        assert len(embeddings) == 4
        # Text rỗng -> zero vector
        assert all(v == 0.0 for v in embeddings[1])
        assert all(v == 0.0 for v in embeddings[2])
        # Valid text -> có embedding
        assert any(v != 0.0 for v in embeddings[0])
        assert any(v != 0.0 for v in embeddings[3])


class TestHealthCheck:
    """Test health check."""

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_health_check_openai_success(self, mock_settings):
        """Health check OpenAI thành công."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(
            return_value=MagicMock()
        )

        result = await service.health_check()
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_health_check_ollama_success(self, mock_settings):
        """Health check Ollama thành công."""
        mock_settings.EMBEDDING_PROVIDER = "ollama"
        mock_settings.OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
        mock_settings.OLLAMA_EMBEDDING_URL = "http://localhost:11434"

        service = EmbeddingService()
        service._ollama_client = MagicMock()
        service._ollama_client.embeddings.create = AsyncMock(
            return_value=MagicMock()
        )

        result = await service.health_check()
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_health_check_failure(self, mock_settings):
        """Health check thất bại khi service không reachable."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        result = await service.health_check()
        assert result is False


class TestFallbackBehavior:
    """Test fallback behavior khi có lỗi."""

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_fallback_zero_vector_on_api_error(self, mock_settings):
        """Trả về zero vector khi API lỗi."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        service = EmbeddingService()
        service._openai_client = MagicMock()
        service._openai_client.embeddings.create = AsyncMock(
            side_effect=Exception("API error")
        )

        embedding = await service.generate_embedding("test")

        # Should return zero vector on error
        assert len(embedding) == EMBEDDING_DIM_OPENAI
        assert all(v == 0.0 for v in embedding)

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.settings")
    async def test_empty_list_returns_empty(self, mock_settings):
        """Empty list input trả về empty list."""
        mock_settings.EMBEDDING_PROVIDER = "openai"
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        service = EmbeddingService()
        result = await service.generate_embeddings([])
        assert result == []
