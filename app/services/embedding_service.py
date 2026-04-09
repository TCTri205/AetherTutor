"""
Embedding Service - Abstraction layer cho embedding generation.

Hỗ trợ 2 providers:
- OpenAI (cloud): text-embedding-3-small, 1536 dimensions
- Ollama (local): nomic-embed-text, 768 dimensions

Provider được chọn qua config EMBEDDING_PROVIDER.
"""

from typing import List, Optional
import logging
import asyncio

from openai import AsyncOpenAI
from ..config import settings
from ..constants import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIM_OPENAI,
    EMBEDDING_DIM_OLLAMA,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service tạo embeddings với abstraction cho multiple providers.
    
    Usage:
        embeddings = await embedding_service.generate_embeddings(["text1", "text2"])
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        openai_model: Optional[str] = None,
        ollama_model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
    ):
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.openai_model = openai_model or settings.OPENAI_EMBEDDING_MODEL
        self.ollama_model = ollama_model or settings.OLLAMA_EMBEDDING_MODEL
        self.ollama_base_url = ollama_base_url or settings.OLLAMA_EMBEDDING_URL

        # Dimension tùy thuộc vào provider
        self.dimension = (
            EMBEDDING_DIM_OPENAI
            if self.provider == "openai"
            else EMBEDDING_DIM_OLLAMA
        )

        # OpenAI client (chỉ khởi tạo nếu provider là openai)
        self._openai_client: Optional[AsyncOpenAI] = None
        if self.provider == "openai":
            api_key = settings.OPENAI_API_KEY
            if api_key and not api_key.startswith("your_"):
                self._openai_client = AsyncOpenAI(api_key=api_key)
            else:
                logger.warning(
                    "OpenAI embedding provider selected but API key is invalid. "
                    "Falling back to Ollama."
                )
                self.provider = "ollama"

        # Ollama client (dùng OpenAI-compatible API qua base_url)
        self._ollama_client: Optional[AsyncOpenAI] = None
        if self.provider == "ollama":
            self._ollama_client = AsyncOpenAI(
                api_key="ollama",  # Ollama không cần API key thật
                base_url=f"{self.ollama_base_url}/v1",
            )

    @property
    def is_local(self) -> bool:
        """Trả về True nếu đang dùng local provider (Ollama)."""
        return self.provider == "ollama"

    @property
    def is_cloud(self) -> bool:
        """Trả về True nếu đang dùng cloud provider (OpenAI)."""
        return self.provider == "openai"

    async def health_check(self) -> bool:
        """Check nếu embedding provider reachable."""
        try:
            if self.provider == "openai" and self._openai_client:
                # Test bằng cách tạo 1 embedding đơn giản
                await self._openai_client.embeddings.create(
                    model=self.openai_model,
                    input="health check"
                )
                return True

            elif self.provider == "ollama" and self._ollama_client:
                await self._ollama_client.embeddings.create(
                    model=self.ollama_model,
                    input="health check"
                )
                return True

        except Exception as e:
            logger.error(f"Embedding health check failed ({self.provider}): {e}")
            return False

        return False

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Tạo embedding cho một đoạn text.
        
        Args:
            text: Input text
            
        Returns:
            List of floats (embedding vector)
        """
        if not text or not text.strip():
            return [0.0] * self.dimension

        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else [0.0] * self.dimension

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo embeddings cho nhiều đoạn text (batch processing).
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Lọc text rỗng
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return [[0.0] * self.dimension] * len(texts)

        # Batch processing để tránh overload API
        all_embeddings = []
        for i in range(0, len(valid_texts), EMBEDDING_BATCH_SIZE):
            batch = valid_texts[i:i + EMBEDDING_BATCH_SIZE]
            batch_embeddings = await self._generate_batch(batch)
            all_embeddings.extend(batch_embeddings)

        # Pad nếu có text rỗng ban đầu
        result = []
        valid_idx = 0
        for original_text in texts:
            if not original_text or not original_text.strip():
                result.append([0.0] * self.dimension)
            else:
                result.append(all_embeddings[valid_idx])
                valid_idx += 1

        return result

    async def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings cho một batch texts."""
        if self.provider == "openai" and self._openai_client:
            return await self._generate_openai_embeddings(texts)
        elif self.provider == "ollama" and self._ollama_client:
            return await self._generate_ollama_embeddings(texts)
        else:
            logger.error(f"No valid embedding provider available. Current: {self.provider}")
            return [[0.0] * self.dimension] * len(texts)

    async def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """OpenAI embedding generation."""
        try:
            response = await self._openai_client.embeddings.create(
                model=self.openai_model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            # Fallback: trả về zero vectors
            return [[0.0] * self.dimension] * len(texts)

    async def _generate_ollama_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Ollama embedding generation via OpenAI-compatible API."""
        try:
            response = await self._ollama_client.embeddings.create(
                model=self.ollama_model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            # Fallback: trả về zero vectors
            return [[0.0] * self.dimension] * len(texts)


# Singleton instance
embedding_service = EmbeddingService()
