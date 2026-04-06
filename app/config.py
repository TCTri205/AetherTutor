from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AetherTutor"
    DEBUG: bool = True
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aethertutor"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100

    # LLM Service
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    
    # Model Selection
    DEFAULT_LLM_MODEL: str = "hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Document Processing
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
