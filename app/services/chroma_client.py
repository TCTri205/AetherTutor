import chromadb
from chromadb.config import Settings as ChromaSettings
from ..config import settings
from ..constants import (
    CHROMA_COLLECTION_NAME_CHUNKS,
    CHROMA_COLLECTION_NAME_ENTITIES,
    CHROMA_HNSW_SPACE,
    EMBEDDING_DIM_OPENAI,
    EMBEDDING_MODEL_NAME_OPENAI,
    EMBEDDING_MODEL_NAME_OLLAMA,
)
import logging
from typing import Optional, List, Dict

# Suppress ChromaDB/PostHog telemetry errors
import os
os.environ["ANONYMIZED_TELEMETRY"] = "false"
try:
    import chromadb.telemetry.product.posthog
    # Replace the problematic capture method with a no-op
    chromadb.telemetry.product.posthog.Posthog._direct_capture = lambda self, *args, **kwargs: None
except Exception:
    pass  # Ignore if telemetry module structure changes

logger = logging.getLogger(__name__)


class ChromaClient:
    """
    Enhanced ChromaDB client with connection and collection caching.
    Hỗ trợ cả implicit embeddings (ChromaDB auto) và explicit embeddings (từ embedding_service).
    
    BR-008: Tự động kiểm tra embedding_dim để tránh xung đột khi đổi model.
    """

    def __init__(self):
        self._client: Optional[chromadb.HttpClient] = None
        self._collections_cache = {}  # Cache collections to avoid repeated get_or_create
        self._current_embedding_dim: Optional[int] = None  # Track current embedding dimension

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
        
        BR-008: Nếu metadata có 'embedding_dim', sẽ validate với collection hiện tại.
        Nếu dimension khác nhau, tạo collection mới với suffix.
        """
        # Nếu collection đã cached, kiểm tra dimension match
        if name in self._collections_cache:
            cached_collection = self._collections_cache[name]
            
            # Nếu có embedding_dim trong metadata, validate
            if metadata and "embedding_dim" in metadata:
                requested_dim = metadata["embedding_dim"]
                existing_dim = cached_collection.metadata.get("embedding_dim")
                
                if existing_dim and existing_dim != requested_dim:
                    # Dimension khác nhau → tạo collection mới
                    new_name = f"{name}_dim{requested_dim}"
                    logger.warning(
                        f"Dimension mismatch for collection '{name}': "
                        f"existing={existing_dim}, requested={requested_dim}. "
                        f"Creating new collection: '{new_name}'"
                    )
                    # Recursive call với tên mới
                    return self._get_collection(new_name, metadata)
            
            return cached_collection

        # Collection chưa tồn tại → tạo mới
        try:
            # Đảm bảo metadata có hnsw:space
            final_metadata = metadata or {"hnsw:space": CHROMA_HNSW_SPACE}
            if "hnsw:space" not in final_metadata:
                final_metadata["hnsw:space"] = CHROMA_HNSW_SPACE

            collection = self.client.get_or_create_collection(
                name=name,
                metadata=final_metadata
            )
            self._collections_cache[name] = collection
            
            # Track current dimension
            if "embedding_dim" in final_metadata:
                self._current_embedding_dim = final_metadata["embedding_dim"]
                logger.info(
                    f"Collection '{name}' created with embedding_dim={final_metadata['embedding_dim']}"
                )
            else:
                logger.info(f"Collection '{name}' created (no embedding_dim specified)")
            
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection '{name}': {e}")
            raise

    def validate_embedding_dimension(self, embedding: List[float], collection_name: str = "unknown") -> bool:
        """
        Validate embedding dimension match với collection hiện tại.
        
        Args:
            embedding: Embedding vector để check
            collection_name: Tên collection (cho logging)
            
        Returns:
            True nếu dimension match hoặc chưa có dimension track
            
        Raises:
            ValueError nếu dimension không khớp
        """
        if not embedding:
            return True
            
        emb_dim = len(embedding)
        
        # Nếu chưa track dimension nào, set luôn
        if self._current_embedding_dim is None:
            self._current_embedding_dim = emb_dim
            logger.info(f"Set embedding dimension to {emb_dim} (first embedding for {collection_name})")
            return True
        
        # Check match
        if self._current_embedding_dim != emb_dim:
            raise ValueError(
                f"Embedding dimension mismatch for {collection_name}: "
                f"expected {self._current_embedding_dim}, got {emb_dim}. "
                f"Thường do đổi embedding model (OpenAI ↔ Ollama)."
            )
        
        return True

    @property
    def chunks_collection(self):
        # BR-008: Thêm embedding_dim vào metadata
        # Dùng dimension từ embedding service hiện tại (nếu available)
        from ..services.embedding_service import embedding_service
        current_dim = embedding_service.dimension if embedding_service else EMBEDDING_DIM_OPENAI
        
        metadata = {
            "hnsw:space": CHROMA_HNSW_SPACE,
            "embedding_dim": current_dim,
            "embedding_model": EMBEDDING_MODEL_NAME_OPENAI if current_dim == EMBEDDING_DIM_OPENAI else EMBEDDING_MODEL_NAME_OLLAMA,
        }
        return self._get_collection(CHROMA_COLLECTION_NAME_CHUNKS, metadata)

    @property
    def entities_collection(self):
        # BR-008: Thêm embedding_dim vào metadata
        from ..services.embedding_service import embedding_service
        current_dim = embedding_service.dimension if embedding_service else EMBEDDING_DIM_OPENAI
        
        metadata = {
            "hnsw:space": CHROMA_HNSW_SPACE,
            "embedding_dim": current_dim,
            "embedding_model": EMBEDDING_MODEL_NAME_OPENAI if current_dim == EMBEDDING_DIM_OPENAI else EMBEDDING_MODEL_NAME_OLLAMA,
        }
        return self._get_collection(CHROMA_COLLECTION_NAME_ENTITIES, metadata)

    def add_to_collection(
        self,
        collection,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ):
        """
        Add documents to a collection with optional explicit embeddings.

        Nếu embeddings được cung cấp, dùng trực tiếp (không để ChromaDB tự generate).
        Nếu không, ChromaDB sẽ tự tạo embeddings (implicit).
        
        BR-008: Validate embedding dimension trước khi add.

        Args:
            collection: ChromaDB collection object
            ids: Document IDs
            documents: Text documents
            metadatas: Metadata cho mỗi document
            embeddings: Pre-computed embeddings (optional)
            
        Raises:
            ValueError: Nếu embedding dimension không khớp
        """
        # BR-008: Validate embedding dimension
        if embeddings:
            # Check dimension của embedding đầu tiên
            first_embedding = embeddings[0] if embeddings else None
            if first_embedding:
                self.validate_embedding_dimension(
                    first_embedding,
                    collection_name=collection.name
                )
            logger.debug(f"Using {len(embeddings)} explicit embeddings for {len(ids)} documents")

        add_kwargs = {
            "ids": ids,
            "documents": documents,
        }

        if metadatas:
            add_kwargs["metadatas"] = metadatas

        if embeddings:
            add_kwargs["embeddings"] = embeddings

        try:
            collection.add(**add_kwargs)
        except Exception as e:
            logger.error(f"Failed to add to collection: {e}")
            raise

    def add_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ):
        """
        Add chunks to the chunks collection.

        ⚠️ BR-002: Tự động thêm content_type="chunk" vào metadata để phân biệt với entities.
        """
        # BR-002: Ensure content_type metadata
        if metadatas:
            for m in metadatas:
                m.setdefault("content_type", "chunk")
        else:
            metadatas = [{"content_type": "chunk"} for _ in ids]

        self.add_to_collection(
            self.chunks_collection,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def add_entities(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ):
        """
        Add entities to the entities collection.

        ⚠️ BR-002: Tự động thêm content_type="entity" vào metadata để phân biệt với chunks.
        """
        # BR-002: Ensure content_type metadata
        if metadatas:
            for m in metadatas:
                m.setdefault("content_type", "entity")
        else:
            metadatas = [{"content_type": "entity"} for _ in ids]

        self.add_to_collection(
            self.entities_collection,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query_collection(
        self,
        collection,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None,
    ):
        """
        Query a collection with either query_texts or query_embeddings.
        
        Ưu tiên query_embeddings nếu được cung cấp (đã có sẵn embedding).
        Nếu chỉ có query_texts, ChromaDB sẽ tự generate query embedding.
        """
        query_kwargs = {
            "n_results": n_results,
        }
        
        if query_embeddings:
            query_kwargs["query_embeddings"] = query_embeddings
            logger.debug(f"Querying with {len(query_embeddings)} explicit query embeddings")
        elif query_texts:
            query_kwargs["query_texts"] = query_texts
            logger.debug(f"Querying with {len(query_texts)} query texts (implicit embedding)")
        
        if where:
            query_kwargs["where"] = where
        
        if include:
            query_kwargs["include"] = include

        return collection.query(**query_kwargs)

    def query_chunks(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ):
        """Query chunks with optional explicit query embeddings."""
        return self.query_collection(
            self.chunks_collection,
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def query_entities(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ):
        """Query entities with optional explicit query embeddings."""
        return self.query_collection(
            self.entities_collection,
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def delete_by_document_id(self, document_id: str):
        """
        Xóa toàn bộ chunks và entities liên quan đến document_id trong ChromaDB.

        ⚠️ BR-008 Multi-Collection Delete:
        Khi user đổi embedding provider (OpenAI ↔ Ollama), collection mới được tạo.
        Document có thể có embeddings ở NHIỀU collections khác nhau.
        PHẢI xóa ở TẤT CẢ collections để tránh orphan vectors.

        Strategy:
            1. Xóa trên collections hiện tại (chunks_collection, entities_collection)
            2. Liệt kê TẤT CẢ collections trong ChromaDB
            3. Xóa document_id trên mọi collection có metadata chứa document_id này
        """
        errors = []

        # 1. Xóa trên collections hiện tại (ưu tiên)
        try:
            self.chunks_collection.delete(where={"document_id": str(document_id)})
        except Exception as e:
            errors.append(f"chunks_collection: {e}")

        try:
            self.entities_collection.delete(where={"document_id": str(document_id)})
        except Exception as e:
            errors.append(f"entities_collection: {e}")

        # 2. Quét TẤT CẢ collections trong ChromaDB để tìm collections cũ
        try:
            all_collection_objs = self.client.list_collections()
            # list_collections() trả về list của Collection objects
            all_collections = [col.name if hasattr(col, 'name') else str(col) for col in all_collection_objs]
            current_names = {
                self.chunks_collection.name,
                self.entities_collection.name,
            }
            for col_name in all_collections:
                if col_name not in current_names:
                    try:
                        col = self.client.get_collection(col_name)
                        col.delete(where={"document_id": str(document_id)})
                        logger.info(f"Deleted document {document_id} from old collection: {col_name}")
                    except Exception:
                        pass  # Bỏ qua collections không liên quan
        except Exception as e:
            errors.append(f"list_collections: {e}")

        if errors:
            logger.error(f"ChromaDB delete errors for document {document_id}: {errors}")
            # Không raise — cố gắng xóa nhiều nhất có thể

    def reset_cache(self):
        """Reset collection cache (useful for testing or reconnection)."""
        self._collections_cache.clear()
        self._client = None
        logger.info("ChromaDB cache reset")

chroma_client = ChromaClient()
