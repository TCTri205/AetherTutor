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

    async def process_document(self, text: str, filename: str) -> str:
        """
        Main ingestion pipeline.
        1. Calculate hash & check uniqueness.
        2. Create doc record.
        3. Chunk text.
        4. Store chunks (SQL & Chroma).
        5. Extract entities (LLM).
        6. Store Graph (SQL & Chroma).
        7. Finalize status.
        """
        content_hash = self._calculate_content_hash(text)
        
        # Check for duplicates
        existing_doc = await self.doc_repo.get_by_hash(content_hash)
        if existing_doc:
            return str(existing_doc.id)

        # Create document
        doc = await self.doc_repo.create(filename, content_hash)
        doc_id = doc.id

        try:
            await self.doc_repo.update_status(doc_id, DocumentStatus.PROCESSING)
            
            # Step 1: Chunking
            raw_chunks = self._chunk_text(text)
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

            # Persistence: Chunks
            await self.chunk_repo.bulk_insert(chunks_to_db)
            chroma_client.chunks_collection.add(
                ids=chroma_ids,
                documents=chroma_docs,
                metadatas=chroma_metas
            )

            # Step 2: Extraction (Extract from whole or by chunk? LLM model is 1.5B, better by chunk if long)
            # For MVP, we'll extract from a combined sample or per-chunk if necessary.
            # Plan says: "Xóa sổ các Entities trùng trong 1 document: gộp Node chung (canonical_name)"
            
            all_entities = []
            all_relations = []
            
            # Extract per chunk for better accuracy with small model
            for chunk_text in raw_chunks:
                extraction = await self.extractor.extract(chunk_text)
                if not extraction:
                    # Ingest failed to extract meaningful data (e.g. LLM API Error)
                    raise Exception("Extraction failed completely. Check LLM provider/API key.")
                
                all_entities.extend(extraction.entities)
                all_relations.extend(extraction.relations)

            # Step 3: Map-Reduce Entities (Normalize)
            dedup_entities = self.extractor.deduplicate_entities(all_entities)
            
            # Persistence: Graph
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

            await self.graph_repo.bulk_upsert_entities(entity_data_list, doc_id)
            await self.graph_repo.bulk_upsert_relations(relation_data_list, doc_id)

            # Persistence: Chroma Entities
            entity_chroma_ids = [f"{doc_id}::entity::{e.name}" for e in dedup_entities]
            entity_chroma_docs = [f"{e.name} ({e.entity_type}): {e.description}" for e in dedup_entities]
            entity_chroma_metas = [{"document_id": str(doc_id), "entity_name": e.name} for e in dedup_entities]
            
            if entity_chroma_ids:
                chroma_client.entities_collection.add(
                    ids=entity_chroma_ids,
                    documents=entity_chroma_docs,
                    metadatas=entity_chroma_metas
                )

            await self.doc_repo.update_status(doc_id, DocumentStatus.COMPLETED)
            return str(doc_id)

        except Exception as e:
            await self.doc_repo.update_status(doc_id, DocumentStatus.FAILED, str(e))
            # Rollback Chroma
            try:
                chroma_client.chunks_collection.delete(where={"document_id": str(doc_id)})
                chroma_client.entities_collection.delete(where={"document_id": str(doc_id)})
            except:
                pass
            raise e

    async def retrieve_context(self, query: str, document_id: str) -> List[Dict[str, Any]]:
        return await self.retriever.retrieve(query, document_id)

    async def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        # To be implemented in Retriever or LLMService
        return await self.retriever.generate(query, context)
