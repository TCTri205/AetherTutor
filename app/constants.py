"""
Constants configuration for AetherTutor application.
Centralizes all magic numbers and default values.
"""

# Text Chunking
CHUNK_SIZE = 800  # characters
CHUNK_OVERLAP = 150  # characters
MIN_CHUNK_SIZE = 50  # minimum characters to keep a chunk

# Retrieval
RETRIEVAL_TOP_K_CHUNKS = 5
RETRIEVAL_TOP_K_ENTITIES = 3
RETRIEVAL_HISTORY_LENGTH = 10  # number of recent messages to include in context

# LLM & Streaming
LLM_STREAM_TIMEOUT_SECONDS = 120  # 2 minutes
LLM_TEMPERATURE_CHAT = 0.7
LLM_TEMPERATURE_EXTRACTION = 0.1
LLM_MAX_RETRIES = 3
LLM_MAX_TOKENS_TITLE_GENERATION = 20

# Rate Limiting
RATE_LIMIT_DOCUMENT_UPLOAD = "5/minute"
RATE_LIMIT_DOCUMENT_DELETE = "20/minute"
RATE_LIMIT_CONVERSATION_CREATE = "20/minute"
RATE_LIMIT_CHAT_STREAM = "60/minute"

# Worker & Queue
WORKER_JOB_TIMEOUT_SECONDS = 600  # 10 minutes
WORKER_MAX_RETRIES = 3

# ChromaDB
CHROMA_COLLECTION_NAME_CHUNKS = "aethertutor_chunks"
CHROMA_COLLECTION_NAME_ENTITIES = "aethertutor_entities"
CHROMA_HNSW_SPACE = "cosine"

# Entity Extraction
ENTITY_CONFIDENCE_DEFAULT = 0.5

# Pagination
DEFAULT_PAGE_SIZE = 100
DEFAULT_PAGE_SKIP = 0

# File Upload
MIN_CONTENT_LENGTH = 50  # minimum text length to process
