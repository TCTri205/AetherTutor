import chromadb
from chromadb.config import Settings as ChromaSettings
from ..config import settings
from ..constants import (
    CHROMA_COLLECTION_NAME_CHUNKS,
    CHROMA_COLLECTION_NAME_ENTITIES,
    CHROMA_HNSW_SPACE
)
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ChromaClient:
    """
    Enhanced ChromaDB client with connection and collection caching.
    """

    def __init__(self):
        self._client: Optional[chromadb.HttpClient] = None
        self._collections_cache = {}  # Cache collections to avoid repeated get_or_create
    
    @property
    def client(self) -> chromadb.HttpClient:
        """Lazy initialization with caching of ChromaDB client."""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=str(settings.CHROMA_PORT),
                    settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
                )
                logger.info("ChromaDB client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise
        return self._client
    
    def _get_collection(self, name: str, metadata: dict = None):
        """
        Get or create collection with caching.
        Avoids repeated get_or_create calls.
        """
        if name not in self._collections_cache:
            try:
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata=metadata or {"hnsw:space": CHROMA_HNSW_SPACE}
                )
                self._collections_cache[name] = collection
                logger.debug(f"Collection '{name}' cached")
            except Exception as e:
                logger.error(f"Failed to get/create collection '{name}': {e}")
                raise
        return self._collections_cache[name]
    
    @property
    def chunks_collection(self):
        return self._get_collection(CHROMA_COLLECTION_NAME_CHUNKS)
    
    @property
    def entities_collection(self):
        return self._get_collection(CHROMA_COLLECTION_NAME_ENTITIES)
    
    def delete_by_document_id(self, document_id: str):
        """Xóa toàn bộ chunks và entities liên quan đến document_id trong ChromaDB."""
        try:
            self.chunks_collection.delete(where={"document_id": str(document_id)})
            self.entities_collection.delete(where={"document_id": str(document_id)})
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from ChromaDB: {e}")
            raise
    
    def reset_cache(self):
        """Reset collection cache (useful for testing or reconnection)."""
        self._collections_cache.clear()
        self._client = None
        logger.info("ChromaDB cache reset")

chroma_client = ChromaClient()
