from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, delete, or_
from ..models.graph import GraphEntity, GraphRelation
from typing import List, Dict, Any
import uuid

class GraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert_entities(self, entities: List[Dict[str, Any]], document_id: uuid.UUID):
        """
        Upsert entities for a document.
        If canonical_name already exists for this document, update description and confidence.
        """
        if not entities:
            return

        for entity_data in entities:
            stmt = insert(GraphEntity).values(
                document_id=document_id,
                canonical_name=entity_data["canonical_name"],
                entity_type=entity_data["entity_type"],
                description=entity_data["description"],
                confidence=entity_data.get("confidence", 0.5)
            ).on_conflict_do_update(
                constraint="uq_document_entity_name",
                set_={
                    "description": entity_data["description"],
                    "entity_type": entity_data["entity_type"],
                    "confidence": entity_data.get("confidence", 0.5)
                }
            )
            await self.session.execute(stmt)
        await self.session.flush()

    async def bulk_upsert_relations(self, relations: List[Dict[str, Any]], document_id: uuid.UUID):
        """
        Upsert relations for a document.
        """
        if not relations:
            return

        for rel_data in relations:
            stmt = insert(GraphRelation).values(
                document_id=document_id,
                source_entity=rel_data["source_entity"],
                target_entity=rel_data["target_entity"],
                relation_type=rel_data["relation_type"],
                description=rel_data["description"]
            ).on_conflict_do_update(
                constraint="uq_document_relation",
                set_={
                    "description": rel_data["description"],
                    "relation_type": rel_data["relation_type"]
                }
            )
            await self.session.execute(stmt)
        await self.session.flush()

    async def get_entity_neighbors(self, document_id: uuid.UUID, entity_names: List[str]) -> List[GraphRelation]:
        """
        Find all relations where source or target is in the entity_names list.
        """
        if not entity_names:
            return []

        stmt = select(GraphRelation).where(
            GraphRelation.document_id == document_id,
            or_(
                GraphRelation.source_entity.in_(entity_names),
                GraphRelation.target_entity.in_(entity_names)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document_id(self, document_id: uuid.UUID):
        await self.session.execute(
            delete(GraphEntity).where(GraphEntity.document_id == document_id)
        )
        await self.session.execute(
            delete(GraphRelation).where(GraphRelation.document_id == document_id)
        )
        await self.session.flush()
