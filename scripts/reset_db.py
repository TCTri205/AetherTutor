import asyncio
from sqlalchemy import text
from app.database import engine

async def full_cleanup():
    async with engine.begin() as conn:
        print("Cleaning up all LightRAG tables...")
        # Order matters due to foreign keys
        await conn.execute(text("TRUNCATE TABLE graph_relations, graph_entities, document_chunks, documents RESTART IDENTITY CASCADE"))
        print("Done.")

if __name__ == "__main__":
    asyncio.run(full_cleanup())
