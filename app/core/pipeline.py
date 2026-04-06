import uuid
import hashlib
from typing import List, Dict, Any
import tiktoken

from .lightrag import LightRAG
from ..models.document import DocumentStatus
from ..models.graph import DocumentChunk
from ..repositories.document_repo import DocumentRepository
from ..repositories.chunk_repo import ChunkRepository
from ..repositories.graph_repo import GraphRepository
from ..services.chroma_client import chroma_client
from .entity_extractor import EntityExtractor
from .retriever import Retriever
from ..schemas.lightrag import ExtractionResult

class LightRAGPipeline(LightRAG):
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        graph_repo: GraphRepository,
        extractor: EntityExtractor,
        retriever: Retriever
    ):
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.graph_repo = graph_repo
        self.extractor = extractor
        self.retriever = retriever
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _calculate_content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _chunk_text(self, text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
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
            if len(chunk) >= 50: # Drop tiny chunks
                chunks.append(chunk)
            start += chunk_size - chunk_overlap
        return chunks

    async def ingest_text(self, doc_id: uuid.UUID, text: str) -> str:
        """
        Hạt nhân xử lý văn bản:
        1. Chia nhỏ văn bản (Chunking).
        2. Lưu chunks vào PostgreSQL và ChromaDB.
        3. Trích xuất thực thể và quan hệ (Entities & Relations) bằng LLM.
        4. Lưu đồ thị tri thức (Knowledge Graph) vào PostgreSQL và ChromaDB.
        5. Cập nhật trạng thái Document.
        """
        try:
            # Cập nhật trạng thái sang PROCESSING
            await self.doc_repo.update_status(doc_id, DocumentStatus.PROCESSING)
            
            # Bước 1: Chunking
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
                chroma_metas.append({"document_id": str(doc_id), "chunk_index": i})

            # Lưu Chunks vào SQL & Chroma
            await self.chunk_repo.bulk_insert(chunks_to_db)
            chroma_client.chunks_collection.add(
                ids=chroma_ids,
                documents=chroma_docs,
                metadatas=chroma_metas
            )

            # Bước 2: Trích xuất tri thức (Entity & Relation Extraction)
            all_entities = []
            all_relations = []
            
            # Trích xuất theo từng chunk để đảm bảo độ chính xác (đặc biệt với model nhỏ 1.5B)
            for chunk_text in raw_chunks:
                extraction = await self.extractor.extract(chunk_text)
                if extraction:
                    all_entities.extend(extraction.entities)
                    all_relations.extend(extraction.relations)

            # Tối ưu hóa: Loại bỏ các thực thể trùng lặp bằng cách gộp chung (Deduplication)
            dedup_entities = self.extractor.deduplicate_entities(all_entities)
            
            # Chuẩn bị dữ liệu để lưu vào PostgreSQL
            entity_data_list = [
                {
                    "canonical_name": e.name,
                    "entity_type": e.entity_type,
                    "description": e.description,
                    "confidence": e.confidence
                } for e in dedup_entities
            ]
            relation_data_list = [
                {
                    "source_entity": r.source,
                    "target_entity": r.target,
                    "relation_type": r.relation_type,
                    "description": r.description
                } for r in all_relations
            ]

            # Lưu Graph vào SQL
            await self.graph_repo.bulk_upsert_entities(entity_data_list, doc_id)
            await self.graph_repo.bulk_upsert_relations(relation_data_list, doc_id)

            # Bước 3: Lưu Graph vào ChromaDB (để phục vụ retrieval)
            entity_chroma_ids = [f"{doc_id}::entity::{e.name}" for e in dedup_entities]
            entity_chroma_docs = [f"{e.name} ({e.entity_type}): {e.description}" for e in dedup_entities]
            entity_chroma_metas = [{"document_id": str(doc_id), "entity_name": e.name} for e in dedup_entities]
            
            if entity_chroma_ids:
                chroma_client.entities_collection.add(
                    ids=entity_chroma_ids,
                    documents=entity_chroma_docs,
                    metadatas=entity_chroma_metas
                )

            # Hoàn tất
            await self.doc_repo.update_status(doc_id, DocumentStatus.COMPLETED)
            return str(doc_id)

        except Exception as e:
            # Ghi nhận lỗi vào DB
            await self.doc_repo.update_status(doc_id, DocumentStatus.FAILED, str(e))
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
