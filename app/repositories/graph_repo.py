from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, delete, or_, func
from sqlalchemy.orm import selectinload
from ..models.graph import GraphEntity, GraphRelation
from typing import List, Dict, Any
import uuid
from .base import BaseRepository

class GraphRepository(BaseRepository[GraphEntity]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, GraphEntity)

    async def bulk_upsert_entities(self, entities: List[Dict[str, Any]], document_id: uuid.UUID, user_id: uuid.UUID) -> List[GraphEntity]:
        """
        Bulk upsert entities cho một document bằng single INSERT ... ON CONFLICT.
        Tối ưu: Thay vì N câu lệnh riêng lẻ, dùng 1 câu lệnh bulk.

        Deduplicate input bằng conflict key để tránh PostgreSQL error:
        "ON CONFLICT DO UPDATE command cannot affect row a second time".
        """
        if not entities:
            return []

        # Thêm document_id và user_id vào từng entity
        enriched_entities = [
            {
                "document_id": document_id,
                "user_id": user_id,
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

        NOTE: relations phải có keys "source_entity_id" và "target_entity_id" (UUID FK),
        KHÔNG phải "source_entity"/"target_entity" (string name).
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
        # Conflict constraint: uq_graph_relations_doc_source_target_type(document_id, source_entity_id, target_entity_id, relation_type)
        seen: dict[tuple, dict] = {}
        for rel in enriched_relations:
            key = (rel["document_id"], rel["source_entity_id"], rel["target_entity_id"], rel["relation_type"])
            seen[key] = rel
        deduped = list(seen.values())

        stmt = insert(GraphRelation).values(deduped).on_conflict_do_update(
            constraint="uq_graph_relations_doc_source_target_type",
            set_={
                "description": insert(GraphRelation).excluded.description,
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
        stmt = (
            select(GraphRelation)
            .options(
                selectinload(GraphRelation.source_entity),
                selectinload(GraphRelation.target_entity),
            )
            .where(GraphRelation.document_id == document_id)
        )
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
        Find all relations where source or target entity's canonical_name is in the entity_names list.

        NOTE: GraphRelation now uses UUID FK (source_entity_id, target_entity_id)
        thay vì string name. Phải resolve canonical_name → entity_id trước.
        """
        if not entity_names:
            return []

        # Step 1: Resolve canonical_name → entity IDs (trong cùng document)
        entity_ids_stmt = (
            select(GraphEntity.id)
            .where(
                GraphEntity.canonical_name.in_(entity_names),
                GraphEntity.document_id == document_id,
            )
        )
        entity_ids_result = await self.session.execute(entity_ids_stmt)
        entity_ids = [row[0] for row in entity_ids_result.all()]

        if not entity_ids:
            return []

        # Step 2: Query relations by UUID FK
        stmt = select(GraphRelation).where(
            GraphRelation.document_id == document_id,
            or_(
                GraphRelation.source_entity_id.in_(entity_ids),
                GraphRelation.target_entity_id.in_(entity_ids),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_entities_by_document(
        self,
        document_id: uuid.UUID,
        min_confidence: float = 0.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lấy entities của document với confidence filter.
        Returns list of dicts với format phù hợp cho flashcard generation.
        """
        stmt = (
            select(GraphEntity)
            .where(
                GraphEntity.document_id == document_id,
                GraphEntity.confidence >= min_confidence
            )
            .order_by(GraphEntity.confidence.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "name": e.canonical_name,
                "description": e.description or "",
                "entity_type": e.entity_type,
                "confidence": e.confidence
            }
            for e in entities
        ]

    async def delete_by_document_id(self, document_id: uuid.UUID):
        await self.session.execute(
            delete(GraphEntity).where(GraphEntity.document_id == document_id)
        )
        await self.session.execute(
            delete(GraphRelation).where(GraphRelation.document_id == document_id)
        )
        await self.session.flush()
