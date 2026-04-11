import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models.graph import GraphRelation, GraphEntity
from ..repositories.graph_repo import GraphRepository

logger = logging.getLogger(__name__)

class BacklinkService:
    """
    Service to compute and fetch backlinks (incoming relations) for entities.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GraphRepository(db)

    async def get_backlinks(self, entity_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Fetch all relations where target_entity_id is the given entity_id.
        """
        stmt = (
            select(GraphRelation)
            .options(selectinload(GraphRelation.source_entity))
            .where(GraphRelation.target_entity_id == entity_id)
        )
        
        result = await self.db.execute(stmt)
        relations = result.scalars().all()
        
        return [
            {
                "id": str(r.id),
                "source_id": str(r.source_entity_id),
                "source_name": r.source_entity.canonical_name,
                "relation_type": r.relation_type,
                "description": r.description,
                "source": r.source,
                "metadata": r.metadata_
            }
            for r in relations
        ]

    async def create_reverse_relations(self, document_id: Optional[uuid.UUID], relations: List[GraphRelation]):
        """
        Optionally create explicit reverse relations marked as backlinks.
        """
        # Implementation depends on whether we want explicit symmetry in DB
        # or just query incoming relations. The plan says "Compute and cache backlinks".
        # For now, let's assume we use get_backlinks for dynamic retrieval.
        pass
