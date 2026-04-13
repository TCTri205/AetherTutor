from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import settings
from .api import documents, chat, graph, flashcards, quiz, notes, auth, users, topics, agents, collaboration, push, media
from .api.limiter import limiter
from .worker.queue import get_redis_pool
from contextlib import asynccontextmanager
from .services.llm_service import llm_service
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .logging_config import setup_logging, get_logger
from .middleware import RequestLoggingMiddleware
from .core.exceptions import AppError
from .api.websocket_handlers import router as ws_router

# Setup logging
setup_logging(
    level="DEBUG" if settings.DEBUG else "INFO",
    json_format=settings.APP_ENV == "production"
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AetherTutor application...")

    # Security: refuse to start with weak JWT secret in production
    if settings.APP_ENV == "production" and settings.is_weak_jwt_secret:
        raise RuntimeError(
            "Refusing to start with default JWT secret in production. "
            "Set JWT_SECRET_KEY in .env to a strong random value."
        )
    if settings.APP_ENV == "development" and settings.is_weak_jwt_secret:
        logger.warning(
            "SECURITY: Using default JWT secret. Set JWT_SECRET_KEY in production!"
        )

    app.state.arq_pool = await get_redis_pool()
    logger.info("ARQ Redis pool initialized")
    yield
    # Shutdown
    logger.info("Shutting down AetherTutor application...")
    if app.state.arq_pool:
        await app.state.arq_pool.close()
        logger.info("ARQ Redis pool closed")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AetherTutor - Your Agentic Learning OS (LightRAG Powered)",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan
)

# Add CORS middleware first (innermost in stack)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware last (outermost in stack — logs ALL requests including CORS preflight)
app.add_middleware(RequestLoggingMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Map custom AppError hierarchy to proper HTTP responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "online",
        "version": "0.1.0"
    }

import redis.asyncio as redis_async
from sqlalchemy import text
from .database import engine
import chromadb

# Health check router for /api/v1/health
health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health_check():
    """
    Detailed health check monitoring internal dependencies.
    """
    results = {
        "postgres": "unhealthy",
        "redis": "unhealthy",
        "chromadb": "unhealthy"
    }
    
    # 1. Test Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            results["postgres"] = "healthy"
    except Exception:
        pass

    # 2. Test Redis
    try:
        r = redis_async.from_url(settings.REDIS_URL)
        if await r.ping():
            results["redis"] = "healthy"
        await r.close()
    except Exception:
        pass

    # 3. Test ChromaDB
    try:
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        if client.heartbeat():
            results["chromadb"] = "healthy"
    except Exception:
        pass

    # 4. S0.6: Test LLM Status
    llm_healthy = await llm_service.health_check()
    provider = "openai" if llm_service.is_openai else "ollama"
    mode = "cloud" if llm_service.is_openai else "local"

    overall_status = "healthy" if all(v == "healthy" for v in results.values()) and llm_healthy else "degraded"
    
    return {
        "status": overall_status,
        "services": results,
        "llm": {
            "model": settings.DEFAULT_LLM_MODEL,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "provider": provider,
            "mode": mode,
            "healthy": llm_healthy
        }
    }

# Include API Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(flashcards.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")

# NEW: Auth, Users, Topics, Agents, Collaboration routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(topics.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(collaboration.router, prefix="/api/v1")
app.include_router(push.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")

# WebSocket router (no /api/v1 prefix for WebSocket)
app.include_router(ws_router)

