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
WORKER_JOB_TIMEOUT_SECONDS = 1800  # 30 minutes (tăng từ 10 phút để xử lý documents lớn)
WORKER_MAX_RETRIES = 3

# ChromaDB
CHROMA_COLLECTION_NAME_CHUNKS = "aethertutor_chunks"
CHROMA_COLLECTION_NAME_ENTITIES = "aethertutor_entities"
CHROMA_HNSW_SPACE = "cosine"

# Embedding
EMBEDDING_DIM_OPENAI = 1536  # text-embedding-3-small
EMBEDDING_DIM_OLLAMA = 768   # nomic-embed-text
EMBEDDING_BATCH_SIZE = 100   # Max texts per batch request

# Entity Extraction
ENTITY_CONFIDENCE_DEFAULT = 0.5
ENTITY_EXTRACTION_BATCH_SIZE = 5  # Number of chunks to process together in 1 LLM call
ENTITY_EXTRACTION_MIN_ENTITIES = 30       # Ngưỡng dừng fallback LLM
ENTITY_EXTRACTION_MAX_LLM_BATCHES = 10    # Giới hạn LLM calls tối đa


# Pagination
DEFAULT_PAGE_SIZE = 100
DEFAULT_PAGE_SKIP = 0

# File Upload
MIN_CONTENT_LENGTH = 50  # minimum text length to process

# =============================================
# Stage 2 Additions
# =============================================

# SM-2 Algorithm
SM2_INITIAL_EASE = 2.5
SM2_MIN_EASE = 1.3
SM2_DEFAULT_QUALITY = 3  # Default quality for "again" review
SM2_DAILY_DIGEST_CRON = "0 8 * * *"  # 8:00 AM daily
REDIS_DISTRIBUTED_LOCK_TTL = 60  # seconds
FLASHCARDS_DUE_DEFAULT_LIMIT = 50
FLASHCARD_GENERATION_BATCH_SIZE = 50  # Max flashcards generated per document

# Data Cleaning (Sprint 0)
ENTITY_NAME_FUZZY_THRESHOLD = 0.85
MAX_UNRESOLVED_ENTITY_PERCENTAGE = 5  # Dừng migration nếu > 5%

# Storage Abstraction (Sprint 0)
GRAPH_STORAGE_BACKEND = "local"  # "local" | "s3"
GRAPH_STORAGE_PATH = "/app/uploads/graphs"

# Quiz (Sprint 2)
MAX_QUIZ_QUESTIONS = 20
QUIZ_DIFFICULTY_SCALE_MIN = 1
QUIZ_DIFFICULTY_SCALE_MAX = 5
QUIZ_QUALITY_RATING_MIN = 1
QUIZ_QUALITY_RATING_MAX = 5
QUIZ_FEEDBACK_FLAG_THRESHOLD = 2  # Flag quiz nếu rating <= 2
QUIZ_FEEDBACK_ANALYSIS_CRON = "0 3 * * 0"  # Sunday 3 AM

# Zettelkasten / Notes (Sprint 3)
NOTE_LINK_SUGGESTION_THRESHOLD = 0.75
BACKLINK_AI_MODEL_MAX_TOKENS = 500

# Entity Alias Resolution (Sprint 4)
ENTITY_ALIAS_SIMILARITY_THRESHOLD = 0.8
CROSS_VERIFICATION_CONTRADICTION_THRESHOLD = 0.7  # Confidence threshold for contradiction detection
MULTI_DOC_MAX_DOCUMENTS = 10  # Max documents to include in multi-doc query
MULTI_DOC_CLAIMS_PER_DOC = 5  # Max claims to extract per doc for cross-verification

# Notification Strategy (Sprint 1)
NOTIFICATION_BROWSER_ENABLED = True
NOTIFICATION_EMAIL_ENABLED = True  # Requires SMTP_HOST, SMTP_USER
NOTIFICATION_TELEGRAM_ENABLED = False  # Stage 3
