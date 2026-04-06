import chromadb
from chromadb.config import Settings as ChromaSettings
from ..config import settings

class ChromaClient:
    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=str(settings.CHROMA_PORT),
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
        )

    def get_or_create_collection(self, name: str, metadata: dict = None):
        return self.client.get_or_create_collection(
            name=name,
            metadata=metadata or {"hnsw:space": "cosine"}
        )

    @property
    def chunks_collection(self):
        return self.get_or_create_collection("aethertutor_chunks")

    @property
    def entities_collection(self):
        return self.get_or_create_collection("aethertutor_entities")

    def delete_by_document_id(self, document_id: str):
        """Xóa toàn bộ chunks và entities liên quan đến document_id trong ChromaDB."""
        self.chunks_collection.delete(where={"document_id": str(document_id)})
        self.entities_collection.delete(where={"document_id": str(document_id)})

chroma_client = ChromaClient()
