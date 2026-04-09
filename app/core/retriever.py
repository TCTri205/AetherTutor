from typing import List, Dict, Any, Optional, Union
import uuid
import asyncio
import logging
from ..services.chroma_client import chroma_client
from ..services.embedding_service import embedding_service
from ..repositories.graph_repo import GraphRepository
from ..services.llm_service import llm_service
from ..config import settings
from ..constants import RETRIEVAL_TOP_K_CHUNKS, RETRIEVAL_TOP_K_ENTITIES

logger = logging.getLogger(__name__)

class Retriever:
    """
    Service responsible for dual-level context retrieval.
    1. Vector Retrieval (Semantic)
    2. Graph Traversal (Relational)
    3. Multi-document Retrieval (Cross-doc reasoning)
    """

    def __init__(self, graph_repo: GraphRepository):
        self.graph_repo = graph_repo

    async def retrieve(self, query: str, document_id: str, user_id: Optional[Union[uuid.UUID, str]] = None, top_k: int = RETRIEVAL_TOP_K_CHUNKS) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Single-document retrieval with user_id filter.

        Args:
            query: User's query string
            document_id: Document UUID to scope retrieval
            user_id: Optional user UUID or string for multi-tenant isolation.
                     If provided, adds user_id to ChromaDB where clause.
                     Accepts both uuid.UUID and str, normalizes to str internally.
            top_k: Number of top chunks to retrieve

        Returns:
            Tuple of (context list, found entity names)
        """
        context = []
        doc_uuid = uuid.UUID(document_id)

        # Normalize user_id to string for ChromaDB metadata consistency
        user_id_str = str(user_id) if user_id else None

        # Build ChromaDB where clause with user_id filter if provided
        chunks_where = {"document_id": document_id}
        entities_where = {"document_id": document_id}

        if user_id_str:
            chunks_where["user_id"] = user_id_str
            entities_where["user_id"] = user_id_str

        # Generate query embedding (nếu available)
        query_embedding = await embedding_service.generate_embedding(query)
        has_embedding = any(v != 0.0 for v in query_embedding)

        # 1. Vector Search: Chunks
        chunks_res = chroma_client.query_chunks(
            query_texts=[query] if not has_embedding else None,
            query_embeddings=[query_embedding] if has_embedding else None,
            n_results=top_k,
            where=chunks_where
        )

        for i in range(len(chunks_res['ids'][0])):
            context.append({
                "type": "chunk",
                "content": chunks_res['documents'][0][i],
                "metadata": chunks_res['metadatas'][0][i],
                "document_id": document_id
            })

        # 2. Vector Search: Entities mentioned in query
        entities_res = chroma_client.query_entities(
            query_texts=[query] if not has_embedding else None,
            query_embeddings=[query_embedding] if has_embedding else None,
            n_results=RETRIEVAL_TOP_K_ENTITIES,
            where=entities_where
        )

        found_entity_names = [m['entity_name'] for m in entities_res['metadatas'][0]]

        # 3. Graph Traversal: Neighbors
        if found_entity_names:
            relations = await self.graph_repo.get_entity_neighbors(doc_uuid, found_entity_names)
            for rel in relations:
                context.append({
                    "type": "relation",
                    "content": f"{rel.source_entity.canonical_name} --({rel.relation_type})--> {rel.target_entity.canonical_name}: {rel.description}",
                    "metadata": {"source": rel.source_entity.canonical_name, "target": rel.target_entity.canonical_name},
                    "document_id": document_id
                })

        return context, found_entity_names

    async def retrieve_multi(
        self,
        query: str,
        user_id: Union[uuid.UUID, str],
        document_ids: Optional[List[str]] = None,
        scope: str = "user_global",
        top_k: int = RETRIEVAL_TOP_K_CHUNKS,
    ) -> tuple[List[Dict[str, Any]], List[str], Optional[Dict[str, Any]]]:
        """
        Multi-document retrieval with cross-document reasoning.

        Args:
            query: User's query string
            user_id: User UUID (or string) for multi-tenant isolation. Normalized to str internally.
            document_ids: Optional list of document UUIDs to scope retrieval.
                         If None, searches across all user's documents.
            scope: "document" (scoped to specific docs) | "user_global" (all user docs)
            top_k: Number of top chunks to retrieve PER document

        Returns:
            Tuple of (context list, found entity names, cross_verification_summary)
            - cross_verification_summary is None if single-doc retrieval
        """
        # Normalize user_id to string
        user_id_str = str(user_id) if user_id else None
        all_context = []
        all_entity_names = []
        doc_entity_map = {}  # document_id -> list of entities
        doc_context_map = {}  # document_id -> list of context items

        # Determine which documents to search
        if document_ids:
            target_doc_ids = document_ids
        else:
            # Global search: retrieve from all user's documents
            # Use ChromaDB metadata filter with user_id only
            target_doc_ids = None

        if target_doc_ids:
            # Scoped search: retrieve from specific documents
            tasks = []
            for doc_id in target_doc_ids:
                tasks.append(self.retrieve(query, doc_id, user_id=user_id_str, top_k=top_k))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Retrieval failed for doc {target_doc_ids[idx]}: {result}")
                    continue
                
                doc_id = target_doc_ids[idx]
                context, entity_names = result
                all_context.extend(context)
                all_entity_names.extend(entity_names)
                doc_entity_map[doc_id] = entity_names
                doc_context_map[doc_id] = context
        else:
            # Global search: retrieve from all documents with user_id filter
            context, entity_names, global_doc_entity_map = await self._retrieve_global(query, user_id_str, top_k * 3)
            all_context = context
            all_entity_names = entity_names

            # Group by document_id from metadata
            for ctx_item in context:
                doc_id = ctx_item.get("metadata", {}).get("document_id", "unknown")
                if doc_id not in doc_context_map:
                    doc_context_map[doc_id] = []
                doc_context_map[doc_id].append(ctx_item)

            # Merge entity-to-document mapping from global search
            doc_entity_map.update(global_doc_entity_map)

        # Deduplicate entity names
        all_entity_names = list(set(all_entity_names))

        # Deduplicate context items by (document_id, chunk_index) to avoid duplicates
        # when the same chunk ranks high for multiple documents
        seen_context_keys = set()
        deduped_context = []
        for ctx_item in all_context:
            doc_id = ctx_item.get("metadata", {}).get("document_id", "unknown")
            chunk_index = ctx_item.get("metadata", {}).get("chunk_index")
            ctx_type = ctx_item.get("type")
            # Create unique key: for chunks use (doc_id, chunk_index), for relations use (doc_id, content)
            if ctx_type == "chunk" and chunk_index is not None:
                ctx_key = (doc_id, chunk_index)
            else:
                # For relations and other types, use content hash
                ctx_key = (doc_id, ctx_item.get("content", "")[:100])
            
            if ctx_key not in seen_context_keys:
                seen_context_keys.add(ctx_key)
                deduped_context.append(ctx_item)
        
        all_context = deduped_context

        # Cross-verification summary if multi-doc
        cross_verification = None
        if len(doc_context_map) > 1 or (document_ids and len(document_ids) > 1):
            cross_verification = await self._build_cross_verification_summary(
                query=query,
                doc_context_map=doc_context_map,
                doc_entity_map=doc_entity_map,
            )

        return all_context, all_entity_names, cross_verification

    async def _retrieve_global(
        self,
        query: str,
        user_id: str,
        top_k: int,
    ) -> tuple[List[Dict[str, Any]], List[str], Dict[str, List[str]]]:
        """
        Global retrieval across all user's documents.
        Uses ChromaDB with only user_id filter (no document_id filter).

        Args:
            query: User's query string
            user_id: User ID string (already normalized)
            top_k: Number of top chunks to retrieve
            doc_entity_map: Optional dict to populate with entity-to-document mapping
        
        Returns:
            Tuple of (context, entity_names, doc_entity_map)
        """
        doc_entity_map = {}
        context = []

        # Generate query embedding
        query_embedding = await embedding_service.generate_embedding(query)
        has_embedding = any(v != 0.0 for v in query_embedding)

        # 1. Vector Search: Chunks (global, user-only filter)
        chunks_res = chroma_client.query_chunks(
            query_texts=[query] if not has_embedding else None,
            query_embeddings=[query_embedding] if has_embedding else None,
            n_results=top_k,
            where={"user_id": user_id}
        )

        for i in range(len(chunks_res['ids'][0])):
            metadata = chunks_res['metadatas'][0][i]
            doc_id = metadata.get("document_id", "unknown")
            context.append({
                "type": "chunk",
                "content": chunks_res['documents'][0][i],
                "metadata": metadata,
                "document_id": doc_id
            })

        # 2. Vector Search: Entities (global, user-only filter)
        entities_res = chroma_client.query_entities(
            query_texts=[query] if not has_embedding else None,
            query_embeddings=[query_embedding] if has_embedding else None,
            n_results=RETRIEVAL_TOP_K_ENTITIES * 3,
            where={"user_id": user_id}
        )

        found_entity_names = [m['entity_name'] for m in entities_res['metadatas'][0]]

        # Populate entity-to-document mapping from entities metadata
        for meta in entities_res['metadatas'][0]:
            entity_name = meta.get('entity_name')
            doc_id = meta.get('document_id', 'unknown')
            if entity_name:
                if doc_id not in doc_entity_map:
                    doc_entity_map[doc_id] = []
                if entity_name not in doc_entity_map[doc_id]:
                    doc_entity_map[doc_id].append(entity_name)

        # 3. Graph Traversal: Get neighbors for found entities (across all documents)
        if found_entity_names:
            # Get unique document IDs from chunks
            doc_ids_in_context = list(set([
                ctx.get("document_id") for ctx in context
                if ctx.get("document_id") and ctx.get("document_id") != "unknown"
            ]))
            
            # For each document, get entity neighbors and add to context
            for doc_id_str in doc_ids_in_context:
                try:
                    doc_uuid = uuid.UUID(doc_id_str)
                    relations = await self.graph_repo.get_entity_neighbors(doc_uuid, found_entity_names)
                    for rel in relations:
                        context.append({
                            "type": "relation",
                            "content": f"{rel.source_entity.canonical_name} --({rel.relation_type})--> {rel.target_entity.canonical_name}: {rel.description}",
                            "metadata": {"source": rel.source_entity.canonical_name, "target": rel.target_entity.canonical_name},
                            "document_id": doc_id_str
                        })
                except (ValueError, Exception) as e:
                    logger.warning(f"Graph traversal failed for doc {doc_id_str}: {e}")

        return context, found_entity_names, doc_entity_map

    async def _build_cross_verification_summary(
        self,
        query: str,
        doc_context_map: Dict[str, List[Dict[str, Any]]],
        doc_entity_map: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        Build cross-verification summary for multi-document retrieval.
        
        Returns:
        {
            "documents_involved": ["doc_id1", "doc_id2"],
            "claim_sources": [{"claim_snippet": "...", "source_doc": "..."}],
            "potential_contradictions": [...],  # Detected by LLM
            "complementary_info": [...]  # Info that extends other docs
        }
        """
        # Extract key claims from each document's context
        claims_by_doc = {}
        for doc_id, ctx_items in doc_context_map.items():
            snippets = [
                item["content"][:200]
                for item in ctx_items
                if item.get("type") == "chunk"
            ]
            claims_by_doc[doc_id] = snippets[:3]  # Top 3 snippets per doc

        # Use LLM to detect contradictions and complementary info
        contradiction_analysis = await self._detect_contradictions_with_llm(
            query=query,
            claims_by_doc=claims_by_doc,
        )

        return {
            "documents_involved": list(doc_context_map.keys()),
            "claim_sources": [
                {"claim_snippet": snippet[:150], "source_doc": doc_id}
                for doc_id, snippets in claims_by_doc.items()
                for snippet in snippets
            ][:10],  # Limit to 10 claims
            "potential_contradictions": contradiction_analysis.get("contradictions", []),
            "complementary_info": contradiction_analysis.get("complementary", []),
        }

    async def _detect_contradictions_with_llm(
        self,
        query: str,
        claims_by_doc: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """
        Use LLM to detect contradictions between documents.
        Returns dict with 'contradictions' and 'complementary' lists.
        """
        if len(claims_by_doc) < 2:
            return {"contradictions": [], "complementary": []}

        # Build prompt
        doc_claims_str = "\n\n".join([
            f"**Document {doc_id}**:\n" + "\n".join([f"- {claim}" for claim in claims])
            for doc_id, claims in claims_by_doc.items()
        ])

        prompt = f"""You are analyzing information from multiple documents to find contradictions and complementary insights.

Query: {query}

{doc_claims_str}

Analyze the information and return a JSON object with two fields:
1. "contradictions": List of statements that conflict between documents
   Format: "Document A says X, but Document B says Y"
2. "complementary": List of insights that extend or clarify information from other documents
   Format: "Document A mentions P, Document B extends with Q"

Return ONLY valid JSON, no markdown, no extra text.
If no contradictions or complementary info found, return empty lists."""

        try:
            from pydantic import BaseModel, Field
            from typing import List as PydanticList

            class _ContradictionAnalysis(BaseModel):
                contradictions: PydanticList[str] = Field(default_factory=list)
                complementary: PydanticList[str] = Field(default_factory=list)

            response = await llm_service.structured_extraction(
                prompt=prompt,
                response_model=_ContradictionAnalysis,
                max_retries=2,
            )

            if response:
                return {
                    "contradictions": response.contradictions,
                    "complementary": response.complementary,
                }
        except Exception as e:
            logger.warning(f"LLM contradiction detection failed: {e}")

        return {"contradictions": [], "complementary": []}

    async def generate(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        Generate final response using the context.
        """
        context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])
        
        prompt = f"""
        You are a helpful tutor assistant. Answer the question based ONLY on the provided context.
        If the context doesn't contain the answer, say you don't know.

        Context:
        {context_str}

        Question: {query}
        Answer:
        """
        
        response = await llm_service.get_chat_completion([
            {"role": "user", "content": prompt}
        ])
        
        return response.choices[0].message.content

    async def hybrid_search(self, query: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Combine multiple retrieval strategies for best results.
        """
        context = await self.retrieve(query, document_id)
        return context
