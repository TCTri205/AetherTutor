"""
Base repository providing common CRUD operations for all repositories.
"""
from typing import Optional, Type, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
import uuid

T = TypeVar("T", bound=DeclarativeBase)

class BaseRepository(Generic[T]):
    """
    Generic base repository with common CRUD operations.
    All repositories can inherit from this class to reduce boilerplate.
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """Get a single record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID."""
        record = await self.get_by_id(id)
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False
