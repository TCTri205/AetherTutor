import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
import tiktoken

from .lightrag import LightRAG
from ..models.document import DocumentStatus, ProcessingStep
from ..models.graph import DocumentChunk
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..services.chroma_client import chroma_client
from ..services.embedding_service import embedding_service
from .entity_extractor import EntityExtractor
from .retriever import Retriever
from ..constants import (
    CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE, ENTITY_EXTRACTION_BATCH_SIZE
)

logger = logging.getLogger(__name__)

class LightRAGPipeline(LightRAG):
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        graph_repo: GraphRepository,
        extractor: EntityExtractor,
        retriever: Retriever,
        user_id: Optional[uuid.UUID] = None,
    ):
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.graph_repo = graph_repo
        self.extractor = extractor
        self.retriever = retriever
        self.user_id = user_id  # user_id cho multi-tenant isolation trong ChromaDB
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _calculate_content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        Simple fixed-size chunking with character overlap.
        """
        chunks = []
        if len(text) <= chunk_size:
            return [text]

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if len(chunk) >= MIN_CHUNK_SIZE: # Drop tiny chunks
                chunks.append(chunk)
            start += chunk_size - chunk_overlap
        return chunks

    @staticmethod
    def _deduplicate_relations(relations: List[Any]) -> List[Any]:
        """
        Deduplicate relations by (source, target, relation_type) key.
        Keeps the relation with the longest description for richer context.
        """
        seen: dict[tuple, Any] = {}
        for r in relations:
            key = (r.source, r.target, r.relation_type)
            if key not in seen or len(r.description) > len(seen[key].description):
                seen[key] = r
        return list(seen.values())

    async def process_document(self, text: str, document_id: str) -> None:
        """
        Implement abstract method from LightRAG interface.
        Wrapper around ingest_text for compatibility.
        """
        doc_id = uuid.UUID(document_id)
        await self.ingest_text(doc_id, text)

    async def ingest_text(self, doc_id: uuid.UUID, text: str, user_id: Optional[uuid.UUID] = None) -> str:
        """
        Hạt nhân xử lý văn bản:
        1. Chia nhỏ văn bản (Chunking).
        2. Lưu chunks vào PostgreSQL và ChromaDB.
        3. Trích xuất thực thể và quan hệ (Entities & Relations) bằng LLM.
        4. Lưu đồ thị tri thức (Knowledge Graph) vào PostgreSQL và ChromaDB.
        5. Cập nhật trạng thái Document.
        
        Args:
            doc_id: Document UUID
            text: Extracted text content
            user_id: User UUID for multi-tenant isolation in ChromaDB
        """
        # Resolve user_id: prefer explicit param, fallback to instance attribute
        effective_user_id = user_id or self.user_id
        user_id_str = str(effective_user_id) if effective_user_id else None
        
        try:
            # Cập nhật trạng thái sang PROCESSING
            await self.doc_repo.update_status(doc_id, DocumentStatus.PROCESSING)
            
            # Bước 1: Chunking
            await self.doc_repo.update_processing_step(doc_id, ProcessingStep.CHUNKING)
            raw_chunks = self._chunk_text(text)
            if not raw_chunks:
                raise ValueError("Văn bản sau khi trích xuất rỗng hoặc quá ngắn.")

            chunks_to_db = []
            chroma_ids = []
            chroma_docs = []
            chroma_metas = []

            for i, chunk_text in enumerate(raw_chunks):
                chunk_id = f"{doc_id}::chunk::{i}"
                tokens = len(self.tokenizer.encode(chunk_text))
                
                chunks_to_db.append(DocumentChunk(
                    document_id=doc_id,
                    chunk_index=i,
                    content=chunk_text,
                    tokens=tokens
                ))
                
                chroma_ids.append(chunk_id)
                chroma_docs.append(chunk_text)
                chunk_meta = {"document_id": str(doc_id), "chunk_index": i}
                if user_id_str:
                    chunk_meta["user_id"] = user_id_str
                chroma_metas.append(chunk_meta)

            # Lưu Chunks vào SQL
            await self.chunk_repo.bulk_insert(chunks_to_db)
            
            # Generate embeddings cho chunks (nếu embedding service available)
            chunk_embeddings = await embedding_service.generate_embeddings(chroma_docs)

            # Validate: chỉ dùng embeddings nếu TẤT CẢ đều khác zero vector
            def _is_valid_embedding(emb) -> bool:
                return emb is not None and any(v != 0.0 for v in emb)

            has_valid_embeddings = all(_is_valid_embedding(emb) for emb in chunk_embeddings) if chunk_embeddings else False

            chroma_client.add_chunks(
                ids=chroma_ids,
                documents=chroma_docs,
                metadatas=chroma_metas,
                embeddings=chunk_embeddings if has_valid_embeddings else None,
            )

            # Bước 2: Trích xuất tri thức (Entity & Relation Extraction)
            await self.doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING_ENTITIES)
            
            method = getattr(self.extractor._config, "ENTITY_EXTRACTION_METHOD", "llm") if hasattr(self.extractor, "_config") and self.extractor._config else "llm"
            logger.info(f"Starting entity extraction: {len(raw_chunks)} chunks (method={method})")

            extraction = await self.extractor.extract(raw_chunks)
            
            all_entities = []
            all_relations = []
            
            if extraction:
                all_entities = extraction.entities
                all_relations = extraction.relations
                logger.info(f"Entity extraction complete: {len(all_entities)} entities, {len(all_relations)} relations")
            else:
                logger.warning("Entity extraction returned no results")


            # Tối ưu hóa: Loại bỏ các thực thể trùng lặp bằng cách gộp chung (Deduplication)
            dedup_entities = self.extractor.deduplicate_entities(all_entities)
            dedup_relations = self._deduplicate_relations(all_relations)

            # Chuẩn bị dữ liệu entity để lưu vào PostgreSQL
            entity_data_list = [
                {
                    "canonical_name": e.name,
                    "entity_type": e.entity_type,
                    "description": e.description,
                    "confidence": e.confidence
                } for e in dedup_entities
            ]

            # Lưu Graph vào SQL
            await self.doc_repo.update_processing_step(doc_id, ProcessingStep.BUILDING_GRAPH)
            upserted_entities = await self.graph_repo.bulk_upsert_entities(entity_data_list, doc_id, effective_user_id)

            # Build mapping canonical_name → entity.id cho relations
            entity_id_map = {e.canonical_name: e.id for e in upserted_entities}

            # Chuẩn bị relation data với UUID FK (KHÔNG dùng string name)
            relation_data_list = [
                {
                    "source_entity_id": entity_id_map.get(r.source),
                    "target_entity_id": entity_id_map.get(r.target),
                    "relation_type": r.relation_type,
                    "description": r.description
                }
                for r in dedup_relations
                if r.source in entity_id_map and r.target in entity_id_map  # Skip unresolved entities
            ]

            await self.graph_repo.bulk_upsert_relations(relation_data_list, doc_id)

            # Bước 3: Lưu Graph vào ChromaDB (để phục vụ retrieval)
            await self.doc_repo.update_processing_step(doc_id, ProcessingStep.EMBEDDING)
            entity_chroma_ids = [f"{doc_id}::entity::{e.name}" for e in dedup_entities]
            entity_chroma_docs = [f"{e.name} ({e.entity_type}): {e.description}" for e in dedup_entities]
            entity_chroma_metas = []
            for e in dedup_entities:
                e_meta = {"document_id": str(doc_id), "entity_name": e.name}
                if user_id_str:
                    e_meta["user_id"] = user_id_str
                entity_chroma_metas.append(e_meta)
            
            if entity_chroma_ids:
                # Generate embeddings cho entities
                entity_embeddings = await embedding_service.generate_embeddings(entity_chroma_docs)

                # Validate: chỉ dùng embeddings nếu TẤT CẢ đều khác zero vector
                has_valid_entity_embeddings = all(_is_valid_embedding(emb) for emb in entity_embeddings) if entity_embeddings else False

                chroma_client.add_entities(
                    ids=entity_chroma_ids,
                    documents=entity_chroma_docs,
                    metadatas=entity_chroma_metas,
                    embeddings=entity_embeddings if has_valid_entity_embeddings else None,
                )

            # Hoàn tất
            await self.doc_repo.update_status(doc_id, DocumentStatus.COMPLETED)
            return str(doc_id)

        except Exception as e:
            # LƯU Ý: Phải rollback trước khi thực hiện bất kỳ lệnh DB nào tiếp theo
            # vì transaction hiện tại có thể đã bị PostgreSQL đánh dấu là aborted.
            await self.doc_repo.session.rollback()
            
            # Ghi nhận lỗi vào DB dùng transaction mới (sau rollback)
            try:
                await self.doc_repo.update_status(doc_id, DocumentStatus.FAILED, str(e))
                await self.doc_repo.session.commit()
            except Exception as update_err:
                logger.error(f"Không thể cập nhật trạng thái lỗi vào DB: {update_err}")

            # Dọn dẹp ChromaDB phòng trường hợp lỗi giữa chừng để đảm bảo tính nhất quán
            try:
                chroma_client.delete_by_document_id(doc_id)
            except:
                pass
            raise e

    async def retrieve_context(self, query: str, document_id: str) -> List[Dict[str, Any]]:
        return await self.retriever.retrieve(query, document_id)

    async def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        # To be implemented in Retriever or LLMService
        return await self.retriever.generate(query, context)
