import uuid
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from sqlalchemy import select
from ..models.graph import GraphEntity

logger = logging.getLogger(__name__)

class TagService:
    """
    Service to manage entity tags and filter entities by tags.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_tags(self, user_id: uuid.UUID) -> List[str]:
        """
        Get all unique tags used by a user across all their entities.
        """
        # PostgreSQL specific query for array elements
        stmt = sa.text("""
            SELECT DISTINCT unnest(tags) 
            FROM graph_entities 
            WHERE user_id = :user_id
            ORDER BY 1
        """)
        
        result = await self.db.execute(stmt, {"user_id": user_id})
        tags = [row[0] for row in result.all() if row[0]]
        return tags

    async def get_entities_by_tag(self, tag: str, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Search for entities that have a specific tag.
        """
        # Using any() for PostgreSQL array matching
        stmt = (
            select(GraphEntity)
            .where(
                GraphEntity.user_id == user_id,
                GraphEntity.tags.any(tag.lower())
            )
        )
        
        result = await self.db.execute(stmt)
        entities = result.scalars().all()
        
        return [
            {
                "id": str(e.id),
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type,
                "description": e.description,
                "source": e.source,
                "tags": e.tags
            }
            for e in entities
        ]

    async def add_tags_to_entity(self, entity_id: uuid.UUID, tags: List[str]):
        """
        Add new tags to an existing entity, avoiding duplicates.
        """
        stmt = select(GraphEntity).where(GraphEntity.id == entity_id)
        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        
        if entity:
            current_tags = set(entity.tags or [])
            new_tags = [t.lower().strip() for t in tags if t]
            current_tags.update(new_tags)
            entity.tags = list(current_tags)
            await self.db.flush()
            return True
        return False
