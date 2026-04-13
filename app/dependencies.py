from typing import Annotated, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db, set_current_user_id, AsyncSessionLocal
from .api.dependencies import get_current_user_id
import uuid

# Dependency to provide AsyncSession to routes
DBDependency = Annotated[AsyncSession, Depends(get_db)]

async def get_rls_session(user_id: uuid.UUID = Depends(get_current_user_id)) -> AsyncGenerator[AsyncSession, None]:
    """
    RLS-aware session dependency.
    
    Sets the PostgreSQL app.current_user_id context BEFORE yielding the session,
    so that Row-Level Security policies are properly enforced for all queries.
    
    Usage: Replace `get_db` with `get_rls_session` in authenticated endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set RLS context BEFORE any queries
            await set_current_user_id(session, str(user_id))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Backward-compatible alias
RLSDependency = Annotated[AsyncSession, Depends(get_rls_session)]

async def get_current_user(db: DBDependency):
    """
    To be implemented: JWT Auth & User handling.
    For Phase 1 foundation, this is a placeholder.
    """
    return None
