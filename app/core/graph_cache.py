"""
Graph Cache Invalidation Service using Redis.

Strategy:
- When a graph edit succeeds (CREATE/UPDATE/DELETE), set Redis key:
  `graph_cache_invalid:{doc_id}=1` with TTL=30s
- GraphBuilder checks this key before serving cached data
- If key exists, clear in-memory NetworkX graph and rebuild from DB
- Auto-clear key after successful rebuild
"""
import logging
from typing import Optional
import uuid

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

INVALID_KEY_PREFIX = "graph_cache_invalid:"
DEFAULT_TTL_SECONDS = 30


class GraphCacheService:
    """Redis-based cache invalidation for graph edits."""

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self._redis: Optional[aioredis.Redis] = redis_client

    async def get_redis(self) -> aioredis.Redis:
        """Lazy-init Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis

    async def invalidate(self, document_id: uuid.UUID) -> bool:
        """
        Mark graph cache as invalid for a document.
        Sets key `graph_cache_invalid:{doc_id}=1` with TTL.
        Returns True if successful, False if Redis is unavailable.
        """
        try:
            redis_client = await self.get_redis()
            key = f"{INVALID_KEY_PREFIX}{document_id}"
            await redis_client.setex(key, DEFAULT_TTL_SECONDS, "1")
            logger.debug(f"Cache invalidated for document {document_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache invalidation failed (non-critical): {e}")
            return False

    async def is_invalid(self, document_id: uuid.UUID) -> bool:
        """
        Check if graph cache is marked invalid.
        Returns True if invalidation key exists.
        """
        try:
            redis_client = await self.get_redis()
            key = f"{INVALID_KEY_PREFIX}{document_id}"
            exists = await redis_client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.warning(f"Cache check failed (assuming valid): {e}")
            return False

    async def clear_invalid(self, document_id: uuid.UUID) -> bool:
        """
        Remove invalidation key after successful rebuild.
        """
        try:
            redis_client = await self.get_redis()
            key = f"{INVALID_KEY_PREFIX}{document_id}"
            await redis_client.delete(key)
            logger.debug(f"Cache invalidation cleared for document {document_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed (non-critical): {e}")
            return False


# Singleton
_graph_cache: Optional[GraphCacheService] = None


def get_graph_cache() -> GraphCacheService:
    """Get or create the global GraphCacheService singleton."""
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = GraphCacheService()
    return _graph_cache


def reset_graph_cache():
    """Reset singleton (for testing)."""
    global _graph_cache
    _graph_cache = None
