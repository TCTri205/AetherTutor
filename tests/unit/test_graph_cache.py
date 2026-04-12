"""
Unit tests for Stage 3: Graph Cache Invalidation Service.
Tests cover:
- Redis key set/clear/check flow
- TTL behavior
- Error handling (Redis unavailable)
"""
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.graph_cache import (
    GraphCacheService,
    get_graph_cache,
    reset_graph_cache,
    INVALID_KEY_PREFIX,
    DEFAULT_TTL_SECONDS,
)


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def cache(mock_redis):
    """GraphCacheService with mock Redis."""
    service = GraphCacheService(redis_client=mock_redis)
    return service


# ============================================================================
# Invalidation Tests
# ============================================================================

class TestInvalidate:
    """Tests for GraphCacheService.invalidate()."""

    @pytest.mark.asyncio
    async def test_invalidate_sets_key(self, cache, mock_redis):
        """Should set Redis key with TTL."""
        doc_id = uuid.uuid4()
        result = await cache.invalidate(doc_id)

        assert result is True
        expected_key = f"{INVALID_KEY_PREFIX}{doc_id}"
        mock_redis.setex.assert_called_once_with(expected_key, DEFAULT_TTL_SECONDS, "1")

    @pytest.mark.asyncio
    async def test_invalidate_returns_false_on_error(self, cache, mock_redis):
        """Should return False if Redis fails."""
        mock_redis.setex.side_effect = Exception("Connection refused")

        doc_id = uuid.uuid4()
        result = await cache.invalidate(doc_id)

        assert result is False


# ============================================================================
# Check Invalid Tests
# ============================================================================

class TestCheckInvalid:
    """Tests for GraphCacheService.is_invalid()."""

    @pytest.mark.asyncio
    async def test_is_invalid_returns_true_when_key_exists(self, cache, mock_redis):
        """Should return True if invalidation key exists."""
        mock_redis.exists = AsyncMock(return_value=1)

        doc_id = uuid.uuid4()
        result = await cache.is_invalid(doc_id)

        assert result is True
        expected_key = f"{INVALID_KEY_PREFIX}{doc_id}"
        mock_redis.exists.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_is_invalid_returns_false_when_no_key(self, cache, mock_redis):
        """Should return False if invalidation key doesn't exist."""
        mock_redis.exists = AsyncMock(return_value=0)

        doc_id = uuid.uuid4()
        result = await cache.is_invalid(doc_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_invalid_returns_false_on_error(self, cache, mock_redis):
        """Should return False (assuming valid) if Redis fails."""
        mock_redis.exists.side_effect = Exception("Connection refused")

        doc_id = uuid.uuid4()
        result = await cache.is_invalid(doc_id)

        assert result is False


# ============================================================================
# Clear Invalid Tests
# ============================================================================

class TestClearInvalid:
    """Tests for GraphCacheService.clear_invalid()."""

    @pytest.mark.asyncio
    async def test_clear_invalid_deletes_key(self, cache, mock_redis):
        """Should delete invalidation key."""
        doc_id = uuid.uuid4()
        result = await cache.clear_invalid(doc_id)

        assert result is True
        expected_key = f"{INVALID_KEY_PREFIX}{doc_id}"
        mock_redis.delete.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_clear_invalid_returns_false_on_error(self, cache, mock_redis):
        """Should return False if Redis fails."""
        mock_redis.delete.side_effect = Exception("Connection refused")

        doc_id = uuid.uuid4()
        result = await cache.clear_invalid(doc_id)

        assert result is False


# ============================================================================
# Singleton Tests
# ============================================================================

class TestSingleton:
    """Tests for GraphCacheService singleton pattern."""

    def test_get_graph_cache_returns_instance(self):
        """Should return GraphCacheService instance."""
        reset_graph_cache()
        instance = get_graph_cache()
        assert isinstance(instance, GraphCacheService)

    def test_get_graph_cache_returns_same_instance(self):
        """Should return same instance on subsequent calls."""
        reset_graph_cache()
        instance1 = get_graph_cache()
        instance2 = get_graph_cache()
        assert instance1 is instance2

    def test_reset_graph_cache_clears_singleton(self):
        """Should clear global singleton."""
        reset_graph_cache()
        instance = get_graph_cache()
        reset_graph_cache()
        # After reset, next get_graph_cache creates new instance
        new_instance = get_graph_cache()
        assert instance is not new_instance
