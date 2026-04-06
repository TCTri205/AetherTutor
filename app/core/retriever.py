from typing import List, Dict, Any, Optional
import uuid
from ..services.chroma_client import chroma_client
from ..repositories.graph_repo import GraphRepository
from ..services.llm_service import llm_service
from ..config import settings

class Retriever:
    """
    Service responsible for dual-level context retrieval.
    1. Vector Retrieval (Semantic)
    2. Graph Traversal (Relational)
    """
    
    def __init__(self, graph_repo: GraphRepository):
        self.graph_repo = graph_repo

    async def retrieve(self, query: str, document_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Dual-level retrieval from ChromaDB and SQL Graph.
        """
        context = []
        doc_uuid = uuid.UUID(document_id)

        # 1. Vector Search: Chunks
        chunks_res = chroma_client.chunks_collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"document_id": document_id}
        )
        
        for i in range(len(chunks_res['ids'][0])):
            context.append({
                "type": "chunk",
                "content": chunks_res['documents'][0][i],
                "metadata": chunks_res['metadatas'][0][i]
            })

        # 2. Vector Search: Entities mentioned in query
        entities_res = chroma_client.entities_collection.query(
            query_texts=[query],
            n_results=3,
            where={"document_id": document_id}
        )
        
        found_entity_names = [m['entity_name'] for m in entities_res['metadatas'][0]]
        
        # 3. Graph Traversal: Neighbors
        if found_entity_names:
            relations = await self.graph_repo.get_entity_neighbors(doc_uuid, found_entity_names)
            for rel in relations:
                context.append({
                    "type": "relation",
                    "content": f"{rel.source_entity} --({rel.relation_type})--> {rel.target_entity}: {rel.description}",
                    "metadata": {"source": rel.source_entity, "target": rel.target_entity}
                })

        return context

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
