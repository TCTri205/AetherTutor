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

chroma_client = ChromaClient()
 Maryland
