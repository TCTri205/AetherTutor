from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AetherTutor"
    DEBUG: bool = False
    APP_ENV: str = "development"  # development | production
    
    # CORS & App URLs
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:5173"
    APP_URL: str = "http://localhost:8000"

    # Docker Networking — Host Configuration
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100

    # Database Credentials
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "aethertutor"

    # LLM Service
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    USE_LLM_MOCK: bool = False
    
    # Model Selection
    DEFAULT_LLM_MODEL: str = "hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Document Processing
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}

    # Computed URLs
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def ARQ_REDIS_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CHROMA_URL(self) -> str:
        return f"http://{self.CHROMA_HOST}:{self.CHROMA_PORT}"

    @property
    def allowed_origins_list(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            return [self.FRONTEND_URL]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
