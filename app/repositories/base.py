"""
Base repository providing common CRUD operations for all repositories.
"""
from typing import Optional, Type, TypeVar, Generic, Sequence
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
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """Get all records with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID."""
        record = await self.get_by_id(id)
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False
    
    async def count(self) -> int:
        """Get total count of records."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
