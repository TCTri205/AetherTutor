"""
Unit tests for LLM service with retry logic.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_service import LLMService
from app.schemas.lightrag import ExtractionResult
import json


class MockResponse:
    """Mock LLM response."""
    def __init__(self, content: str):
        self.choices = [MagicMock()]
        self.choices[0].message.content = content


class TestLLMServiceRetry:
    """Test LLM service retry logic with exponential backoff."""
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance for testing."""
        return LLMService(api_key="test_key")
    
    @pytest.mark.asyncio
    async def test_structured_extraction_retry_success(self, llm_service):
        """Test that retry succeeds after initial failures."""
        # Create mock responses
        fail_response = MockResponse("invalid json")
        success_response = MockResponse(json.dumps({
            "entities": [{"name": "Test", "entity_type": "CONCEPT", "description": "Test entity", "confidence": 0.9}],
            "relations": []
        }))
        
        # Create an async mock that returns fail, fail, then success
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return fail_response
            return success_response
        
        with patch.object(llm_service.client.chat.completions, 'create', side_effect=mock_create):
            result = await llm_service.structured_extraction(
                "Test prompt",
                ExtractionResult,
                max_retries=3
            )
            
            assert result is not None
            assert len(result.entities) == 1
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_structured_extraction_exhausts_retries(self, llm_service):
        """Test that retry returns None after exhausting all retries."""
        fail_response = MockResponse("invalid json")
        
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return fail_response
        
        with patch.object(llm_service.client.chat.completions, 'create', side_effect=mock_create):
            result = await llm_service.structured_extraction(
                "Test prompt",
                ExtractionResult,
                max_retries=3
            )
            
            assert result is None
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_structured_extraction_validation_error(self, llm_service):
        """Test retry on Pydantic validation errors."""
        incomplete_response = MockResponse(json.dumps({
            "entities": [{"name": "Test"}],  # Missing required fields
            "relations": []
        }))
        
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return incomplete_response
        
        with patch.object(llm_service.client.chat.completions, 'create', side_effect=mock_create):
            result = await llm_service.structured_extraction(
                "Test prompt",
                ExtractionResult,
                max_retries=2
            )
            
            # Should return None due to validation error
            assert result is None
            assert call_count == 2
