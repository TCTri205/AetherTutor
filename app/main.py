from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api import documents, chat, graph
from .worker.queue import get_redis_pool
from contextlib import asynccontextmanager
from .services.llm_service import llm_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo ARQ Pool
    app.state.arq_pool = await get_redis_pool()
    yield
    # Đóng ARQ Pool khi tắt app
    if app.state.arq_pool:
        await app.state.arq_pool.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AetherTutor - Your Agentic Learning OS (LightRAG Powered)",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan
)

# S0.7: Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/health")
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
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")

