"""
Mock LLM Service cho CI/CD và local testing nhanh.

Mock này giả lập AsyncOpenAI client behavior:
- models.list() → trả về dummy models list
- chat.completions.create() → trả về fixed response
- chat.completions.create(stream=True) → async generator giả lập SSE chunks

Cách dùng:
    from tests.mocks.llm_mock import MockLLMService, MockAsyncOpenAI
    
    # Trong test fixtures:
    @pytest.fixture
    def mock_llm():
        return MockLLMService()
    
    # Hoặc patch ở app level:
    @pytest.fixture(autouse=True)
    def patch_llm_service(monkeypatch):
        mock = MockLLMService()
        monkeypatch.setattr("app.services.llm_service.llm_service", mock)
"""

from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel
import json


class MockChatCompletion:
    """Mock response cho non-streaming chat completion"""
    def __init__(self, content: str = "Đây là phản hồi mẫu từ mock LLM."):
        self.choices = [
            MagicMock(
                message=MagicMock(content=content),
                finish_reason="stop"
            )
        ]
        self.model = "mock-model"
        self.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)


class MockChatCompletionChunk:
    """Mock chunk cho streaming chat completion"""
    def __init__(self, content: str, done: bool = False):
        self.choices = [
            MagicMock(
                delta=MagicMock(content=content if not done else None),
                finish_reason="stop" if done else None
            )
        ]
        self.model = "mock-model"


class MockModels:
    """Mock models endpoint"""
    async def list(self) -> List[Any]:
        return [
            MagicMock(id="mock-model-1"),
            MagicMock(id="mock-model-2"),
        ]


class MockChatCompletions:
    """Mock chat.completions endpoint"""
    def __init__(self):
        self.models = MagicMock()

    async def create(
        self,
        model: str = "mock-model",
        messages: List[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        if stream:
            return self._stream_response()
        
        # Non-streaming: trả về fixed response
        return MockChatCompletion()

    async def _stream_response(self) -> AsyncGenerator[MockChatCompletionChunk, None]:
        """Giả lập SSE streaming behavior"""
        # Simulate a few chunks before "done"
        chunks = ["Xin ", "chào! ", "Tôi ", "là ", "mock LLM."]
        for chunk_text in chunks:
            yield MockChatCompletionChunk(content=chunk_text, done=False)
        yield MockChatCompletionChunk(content="", done=True)


class MockAsyncOpenAI:
    """
    Mock AsyncOpenAI client.
    Có cùng interface nhưng trả về dữ liệu giả định.
    """
    def __init__(self, api_key: str = "mock-key", base_url: str = "http://mock"):
        self.api_key = api_key
        self.base_url = base_url
        self.models = MockModels()
        self.chat = MagicMock()
        self.chat.completions = MockChatCompletions()


class MockLLMService:
    """
    Mock LLMService thay thế app.services.llm_service.LLMService.
    Dùng trong tests để không gọi LLM thật.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.is_openai = False
        self.client = MockAsyncOpenAI()

    async def health_check(self) -> bool:
        """Luôn trả về True trong mock"""
        return True

    async def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "mock-model",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Any:
        """Trả về MockChatCompletion"""
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "mock-model",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[MockChatCompletionChunk, None]:
        """Trả về async generator giả lập streaming"""
        async for chunk in self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        ):
            yield chunk

    async def structured_extraction(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: str = "mock-model",
        max_retries: int = 3
    ) -> Optional[BaseModel]:
        """
        Trả về instance rỗng của response_model.
        Useful cho tests cần verify schema validation.
        """
        try:
            # Tạo instance với default values từ model
            return response_model()
        except Exception:
            # Nếu model required fields, trả về None
            return None


def create_mock_llm_service() -> MockLLMService:
    """Helper function để dễ dùng trong fixtures"""
    return MockLLMService()


# === Pytest Fixtures ===

import pytest

@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """Fixture trả về MockLLMService instance"""
    return MockLLMService()


@pytest.fixture
def mock_llm_messages() -> List[Dict[str, str]]:
    """Fixture messages mẫu cho chat tests"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Xin chào!"}
    ]


@pytest.fixture
def mock_llm_response_content() -> str:
    """Fixture response text mặc định"""
    return "Đây là phản hồi mẫu từ mock LLM."
