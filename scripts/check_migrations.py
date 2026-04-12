"""
Migration Fix Script — Check and fix alembic migration state.
"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/aethertutor"


async def check_existing_tables():
    """Check what tables and columns already exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check teams table
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN ('teams', 'team_members', 'shared_resources')"
        )
        print(f"Teams tables found: {[r['table_name'] for r in rows]}")

        # Check graph_entities columns
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='graph_entities' AND column_name IN ('version', 'updated_at') "
            "ORDER BY column_name"
        )
        print(f"graph_entities version/updated_at: {[r['column_name'] for r in rows]}")

        # Check graph_relations columns
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='graph_relations' AND column_name IN ('user_id', 'version', 'updated_at') "
            "ORDER BY column_name"
        )
        print(f"graph_relations user_id/version/updated_at: {[r['column_name'] for r in rows]}")

        # Check graph_edit_log
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='graph_edit_log'"
        )
        print(f"graph_edit_log exists: {len(rows) > 0}")

        # Check quiz_answers bloom_level
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='quiz_answers' AND column_name='bloom_level'"
        )
        print(f"quiz_answers has bloom_level: {len(rows) > 0}")

        # Check documents media_type, source_url
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='documents' AND column_name IN ('media_type', 'source_url') "
            "ORDER BY column_name"
        )
        print(f"documents media_type/source_url: {[r['column_name'] for r in rows]}")

        # Check graph_entities code_snippet, file_size
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='graph_entities' AND column_name IN ('code_snippet', 'file_size') "
            "ORDER BY column_name"
        )
        print(f"graph_entities code_snippet/file_size: {[r['column_name'] for r in rows]}")

        # Check users email_verified
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name IN ('email_verified', 'email_verified_at') "
            "ORDER BY column_name"
        )
        print(f"users email_verified/email_verified_at: {[r['column_name'] for r in rows]}")

        print("\n--- Conclusion ---")
        print("If all columns/tables exist, use 'alembic stamp' instead of upgrade.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_existing_tables())
