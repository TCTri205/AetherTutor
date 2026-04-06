import asyncio
import sys
import os
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import chromadb
from chromadb.config import Settings as ChromaSettings

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

async def test_postgres():
    print("--- Testing PostgreSQL (Async) ---")
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"PostgreSQL Connection: OK (Result: {result.scalar()})")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"PostgreSQL Connection: FAILED - {e}")
        return False

async def test_redis():
    print("\n--- Testing Redis (Async) ---")
    try:
        r = redis.from_url(settings.REDIS_URL)
        ping = await r.ping()
        print(f"Redis Connection: OK (Ping: {ping})")
        await r.close()
        return True
    except Exception as e:
        print(f"Redis Connection: FAILED - {e}")
        return False

def test_chromadb():
    print("\n--- Testing ChromaDB ---")
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        version = client.get_version()
        print(f"ChromaDB Connection: OK (Version: {version})")
        return True
    except Exception as e:
        print(f"ChromaDB Connection: FAILED - {e}")
        return False

async def main():
    print(f"Checking infrastructure connectivity for {settings.PROJECT_NAME}...")
    
    results = await asyncio.gather(
        test_postgres(),
        test_redis()
    )
    
    # ChromaDB test is typically synchronous in its basic client
    results.append(test_chromadb())
    
    print("\n" + "="*30)
    if all(results):
        print("Final Status: ALL CONNECTIONS OK")
    else:
        print("Final Status: SOME CONNECTIONS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
