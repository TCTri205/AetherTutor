from abc import ABC, abstractmethod
from typing import Any, List, Dict

class LightRAG(ABC):
    """
    Abstract interface for the LightRAG pipeline.
    Ensures consistent interaction between high-level services and RAG logic.
    """
    
    @abstractmethod
    async def process_document(self, text: str, document_id: str) -> None:
        """
        Extract entities, build a graph, and persist the results.
        """
        pass

    @abstractmethod
    async def retrieve_context(self, query: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Perform dual-level retrieval from the knowledge graph.
        """
        pass

    @abstractmethod
    async def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        Generate a response based on retrieved knowledge context.
        """
        pass
