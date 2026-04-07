from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, delete, or_, func
from ..models.graph import GraphEntity, GraphRelation
from typing import List, Dict, Any
import uuid
from .base import BaseRepository

class GraphRepository(BaseRepository[GraphEntity]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, GraphEntity)

    async def bulk_upsert_entities(self, entities: List[Dict[str, Any]], document_id: uuid.UUID) -> List[GraphEntity]:
        """
        Bulk upsert entities cho một document bằng single INSERT ... ON CONFLICT.
        Tối ưu: Thay vì N câu lệnh riêng lẻ, dùng 1 câu lệnh bulk.

        Deduplicate input bằng conflict key để tránh PostgreSQL error:
        "ON CONFLICT DO UPDATE command cannot affect row a second time".
        """
        if not entities:
            return []

        # Thêm document_id vào từng entity
        enriched_entities = [
            {
                "document_id": document_id,
                **entity_data
            }
            for entity_data in entities
        ]

        # Deduplicate: giữ record cuối cùng cho mỗi conflict key.
        # Conflict constraint: uq_document_entity_name(document_id, canonical_name)
        seen: dict[tuple, dict] = {}
        for ent in enriched_entities:
            key = (ent["document_id"], ent["canonical_name"])
            seen[key] = ent
        deduped = list(seen.values())

        stmt = insert(GraphEntity).values(deduped).on_conflict_do_update(
            constraint="uq_document_entity_name",
            set_={
                "description": insert(GraphEntity).excluded.description,
                "entity_type": insert(GraphEntity).excluded.entity_type,
                "confidence": insert(GraphEntity).excluded.confidence,
            }
        ).returning(GraphEntity)
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())

    async def bulk_upsert_relations(self, relations: List[Dict[str, Any]], document_id: uuid.UUID) -> List[GraphRelation]:
        """
        Bulk upsert relations cho một document bằng single INSERT ... ON CONFLICT.
        Tối ưu: Thay vì N câu lệnh riêng lẻ, dùng 1 câu lệnh bulk.

        Deduplicate input bằng conflict key để tránh PostgreSQL error:
        "ON CONFLICT DO UPDATE command cannot affect row a second time".
        """
        if not relations:
            return []

        # Thêm document_id vào từng relation
        enriched_relations = [
            {
                "document_id": document_id,
                **rel_data
            }
            for rel_data in relations
        ]

        # Deduplicate: giữ record cuối cùng cho mỗi conflict key.
        # Conflict constraint: uq_document_relation(document_id, source_entity, target_entity, relation_type)
        seen: dict[tuple, dict] = {}
        for rel in enriched_relations:
            key = (rel["document_id"], rel["source_entity"], rel["target_entity"], rel["relation_type"])
            seen[key] = rel
        deduped = list(seen.values())

        stmt = insert(GraphRelation).values(deduped).on_conflict_do_update(
            constraint="uq_document_relation",
            set_={
                "description": insert(GraphRelation).excluded.description,
                "relation_type": insert(GraphRelation).excluded.relation_type,
            }
        ).returning(GraphRelation)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())

    async def get_all_entities(self, document_id: uuid.UUID) -> List[GraphEntity]:
        stmt = select(GraphEntity).where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_relations(self, document_id: uuid.UUID) -> List[GraphRelation]:
        stmt = select(GraphRelation).where(GraphRelation.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_entities(self, document_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(GraphEntity).where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_relations(self, document_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(GraphRelation).where(GraphRelation.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

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
