from fastapi import FastAPI, Depends
from .config import settings
from .api import documents, chat, graph

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AetherTutor - Your Agentic Learning OS (LightRAG Powered)",
    version="0.1.0",
    docs_url="/docs"
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

    overall_status = "healthy" if all(v == "healthy" for v in results.values()) else "degraded"
    
    return {
        "status": overall_status,
        "services": results
    }


# Include API Routers
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")

