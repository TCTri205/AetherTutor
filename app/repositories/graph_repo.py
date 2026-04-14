from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import sqlalchemy as sa
from sqlalchemy import select, delete, or_, func
from sqlalchemy.orm import selectinload
from ..models.graph import GraphEntity, GraphRelation, GraphEditLog
from ..core.exceptions import DuplicateResourceError, ResourceNotFoundError
from typing import List, Dict, Any, Optional
import uuid
from .base import BaseRepository
import logging

logger = logging.getLogger(__name__)

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
                "source": insert(GraphEntity).excluded.source,
                "tags": insert(GraphEntity).excluded.tags,
                "file_path": insert(GraphEntity).excluded.file_path,
                "metadata": sa.text("graph_entities.metadata || EXCLUDED.metadata"), # Merge JSONB
            }
        ).returning(GraphEntity)
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())
    async def upsert_entity(self, user_id: uuid.UUID, document_id: Optional[uuid.UUID], entity_data: Dict[str, Any]) -> GraphEntity:
        """
        Upsert a single entity. If document_id is None, it's considered a 'global' or 'unsorted' entity.
        Note: The unique constraint is on (document_id, canonical_name).
        If document_id is None, we need a special document_id or handle it differently.
        For now, let's assume Obsidian imports use a 'global' document_id or we use document_id=uuid.NAMESPACE_DNS as placeholder.
        """
        doc_id = document_id or uuid.NAMESPACE_DNS # Placeholder for global
        entities = await self.bulk_upsert_entities([entity_data], doc_id, user_id)
        return entities[0]

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
                "source": insert(GraphRelation).excluded.source,
                "is_backlink": insert(GraphRelation).excluded.is_backlink,
                "metadata": sa.text("graph_relations.metadata || EXCLUDED.metadata"), # Merge JSONB
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

    async def batch_get_entities_and_relations(
        self, document_ids: List[uuid.UUID]
    ) -> tuple[Dict[uuid.UUID, List[GraphEntity]], Dict[uuid.UUID, List[GraphRelation]]]:
        """
        Batch fetch entities and relations for multiple documents in single queries.

        Returns:
            Tuple of (entities_by_doc_id, relations_by_doc_id)
            Each is a dict mapping document_id to list of entities/relations.
        """
        if not document_ids:
            return {}, {}

        # Single query for all entities
        entities_stmt = select(GraphEntity).where(
            GraphEntity.document_id.in_(document_ids)
        )
        entities_result = await self.session.execute(entities_stmt)
        all_entities = entities_result.scalars().all()

        # Single query for all relations with eager loading
        relations_stmt = (
            select(GraphRelation)
            .options(
                selectinload(GraphRelation.source_entity),
                selectinload(GraphRelation.target_entity),
            )
            .where(GraphRelation.document_id.in_(document_ids))
        )
        relations_result = await self.session.execute(relations_stmt)
        all_relations = relations_result.scalars().all()

        # Group by document_id
        entities_by_doc = {}
        for entity in all_entities:
            doc_id = entity.document_id
            if doc_id not in entities_by_doc:
                entities_by_doc[doc_id] = []
            entities_by_doc[doc_id].append(entity)

        relations_by_doc = {}
        for relation in all_relations:
            doc_id = relation.document_id
            if doc_id not in relations_by_doc:
                relations_by_doc[doc_id] = []
            relations_by_doc[doc_id].append(relation)

        return entities_by_doc, relations_by_doc

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

    async def get_entity_types_by_names(
        self,
        user_id: uuid.UUID,
        canonical_names: List[str],
    ) -> Dict[str, str]:
        """
        Get entity_type for a list of canonical names, scoped to a user.
        Returns dict mapping canonical_name -> entity_type.
        """
        if not canonical_names:
            return {}

        stmt = (
            select(GraphEntity.canonical_name, GraphEntity.entity_type)
            .where(
                GraphEntity.canonical_name.in_(canonical_names),
                GraphEntity.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # If multiple entities share the same name, take the first one
        return {row.canonical_name: row.entity_type for row in rows}

    async def delete_by_document_id(self, document_id: uuid.UUID):
        """
        Xóa dữ liệu graph liên quan đến document — AN TOÀN cho cross-document entities.

        ⚠️ CRITICAL — Entity-Document Many-to-Many (junction table):
        Entities có thể được chia sẻ giữa nhiều documents qua entity_documents.
        KHÔNG được xóa trực tiếp graph_entities theo document_id.

        Thứ tự xóa:
            1. Xóa graph_relations của document này
            2. Xóa junction records (entity_documents) của document này
            3. Cleanup orphan entities — entities không còn document nào link tới
        """
        from ..models.entity_document import EntityDocument

        # 1. Xóa relations của document này
        await self.session.execute(
            delete(GraphRelation).where(GraphRelation.document_id == document_id)
        )

        # 2. Xóa junction records — unlink document khỏi entities
        await self.session.execute(
            delete(EntityDocument).where(EntityDocument.document_id == document_id)
        )

        # 3. Cleanup orphan entities — entities không còn document nào link tới
        orphan_cleanup = (
            delete(GraphEntity).where(
                GraphEntity.id.notin_(
                    select(EntityDocument.entity_id).distinct()
                )
            )
        )
        await self.session.execute(orphan_cleanup)

        await self.session.flush()

    async def migrate_relations(self, old_entity_id: uuid.UUID, new_entity_id: uuid.UUID):
        """
        Di chuyển toàn bộ quan hệ (source và target) từ thực thể cũ sang thực thể mới.
        Xử lý xung đột UniqueConstraint nếu quan hệ đã tồn tại ở thực thể mới.
        """
        # 1. Update source_entity_id
        # Chúng ta thực hiện từng dòng để dễ xử lý xung đột hoặc dùng UPSERT logic
        stmt_source = (
            sa.update(GraphRelation)
            .where(GraphRelation.source_entity_id == old_entity_id)
            .values(source_entity_id=new_entity_id)
        )
        
        # 2. Update target_entity_id
        stmt_target = (
            sa.update(GraphRelation)
            .where(GraphRelation.target_entity_id == old_entity_id)
            .values(target_entity_id=new_entity_id)
        )

        try:
            await self.session.execute(stmt_source)
            await self.session.execute(stmt_target)
        except sa.exc.IntegrityError:
            # Nếu xảy ra xung đột UniqueConstraint, ta cần xử lý thủ công:
            # Tìm các quan hệ gây xung đột, xóa chúng và giữ lại quan hệ cũ (hoặc ngược lại)
            await self.session.rollback()
            
            # Cách an toàn hơn: Lấy tất cả quan hệ cũ, thử cập nhật từng cái, nếu lỗi thì xóa
            relations_stmt = select(GraphRelation).where(
                or_(
                    GraphRelation.source_entity_id == old_entity_id,
                    GraphRelation.target_entity_id == old_entity_id
                )
            )
            res = await self.session.execute(relations_stmt)
            relations = res.scalars().all()
            
            for rel in relations:
                try:
                    if rel.source_entity_id == old_entity_id:
                        rel.source_entity_id = new_entity_id
                    if rel.target_entity_id == old_entity_id:
                        rel.target_entity_id = new_entity_id
                    await self.session.flush()
                except sa.exc.IntegrityError:
                    await self.session.rollback()
                    # Quan hệ này đã tồn tại ở thực thể mới, xóa quan hệ cũ
                    await self.session.delete(rel)
                    await self.session.flush()

        await self.session.flush()

    async def get_all_entities_for_document(self, document_id: uuid.UUID) -> List[GraphEntity]:
        """Lấy tất cả entities của một document."""
        stmt = select(GraphEntity).where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_relations_for_document(self, document_id: uuid.UUID) -> List[GraphRelation]:
        """Lấy tất cả relations của một document kèm entity info."""
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

    async def get_user_entities(self, user_id: uuid.UUID) -> List[GraphEntity]:
        """Lấy tất cả entities của một user (global graph)."""
        stmt = select(GraphEntity).where(GraphEntity.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_entities_by_names(self, user_id: uuid.UUID, names: List[str]) -> Dict[str, GraphEntity]:
        """
        Lookup entities by canonical_name for a given user.
        Returns a dict mapping entity name -> GraphEntity.
        """
        if not names:
            return {}
        stmt = select(GraphEntity).where(
            GraphEntity.user_id == user_id,
            GraphEntity.canonical_name.in_(names)
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        return {e.canonical_name: e for e in entities}

    async def get_user_relations(self, user_id: uuid.UUID) -> List[GraphRelation]:
        """Lấy tất cả relations của một user (global graph)."""
        stmt = (
            select(GraphRelation)
            .options(
                selectinload(GraphRelation.source_entity),
                selectinload(GraphRelation.target_entity),
            )
            .where(GraphRelation.source_entity.has(user_id=user_id))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # Stage 3: Interactive Graph Editing — CRUD Operations
    # =========================================================================

    async def create_entity(
        self,
        entity_data: Dict[str, Any],
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> GraphEntity:
        """
        Create a new graph entity.
        Validates uniqueness of (document_id, canonical_name).
        """
        # Check for duplicate
        existing = await self.session.execute(
            select(GraphEntity).where(
                GraphEntity.document_id == document_id,
                GraphEntity.canonical_name == entity_data.get("canonical_name"),
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(
                message=f"Entity '{entity_data.get('canonical_name')}' already exists in this document",
                details={"canonical_name": entity_data.get("canonical_name"), "document_id": str(document_id)}
            )

        entity = GraphEntity(
            document_id=document_id,
            user_id=user_id,
            **entity_data
        )
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update_entity(
        self,
        entity_id: uuid.UUID,
        updates: Dict[str, Any],
        expected_version: int,
        user_id: uuid.UUID,
    ) -> GraphEntity:
        """
        Update an entity with optimistic concurrency control.
        Raises DuplicateResourceError (409) if version mismatch.
        """
        # Raw SQL for optimistic concurrency: WHERE id = ? AND version = ?
        stmt = (
            sa.update(GraphEntity)
            .where(
                GraphEntity.id == entity_id,
                GraphEntity.user_id == user_id,
                GraphEntity.version == expected_version,
            )
            .values(
                **updates,
                version=GraphEntity.version + 1,
            )
            .returning(GraphEntity)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()
        entity = result.scalar_one_or_none()

        if not entity:
            # Check if entity exists but version mismatch
            existing = await self.session.execute(
                select(GraphEntity).where(
                    GraphEntity.id == entity_id,
                    GraphEntity.user_id == user_id,
                )
            )
            existing_entity = existing.scalar_one_or_none()
            if existing_entity:
                raise DuplicateResourceError(
                    message="Edit conflict: entity was modified by another user",
                    details={"current_version": existing_entity.version, "expected_version": expected_version}
                )
            raise ResourceNotFoundError(
                resource="Entity",
                identifier=str(entity_id)
            )

        return entity

    async def delete_entity(
        self,
        entity_id: uuid.UUID,
        expected_version: int,
        user_id: uuid.UUID,
    ) -> bool:
        """
        Delete an entity with optimistic concurrency check.
        Cascade deletes related relations via FK constraint.
        """
        stmt = (
            delete(GraphEntity)
            .where(
                GraphEntity.id == entity_id,
                GraphEntity.user_id == user_id,
                GraphEntity.version == expected_version,
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount == 0:
            # Check if entity exists but version mismatch
            existing = await self.session.execute(
                select(GraphEntity).where(
                    GraphEntity.id == entity_id,
                    GraphEntity.user_id == user_id,
                )
            )
            existing_entity = existing.scalar_one_or_none()
            if existing_entity:
                raise DuplicateResourceError(
                    message="Edit conflict: entity was modified by another user",
                    details={"current_version": existing_entity.version, "expected_version": expected_version}
                )
            raise ResourceNotFoundError(
                resource="Entity",
                identifier=str(entity_id)
            )

        return True

    async def create_relation(
        self,
        relation_data: Dict[str, Any],
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> GraphRelation:
        """
        Create a new graph relation.
        Validates that source and target entities exist.
        """
        source_id = relation_data.get("source_entity_id")
        target_id = relation_data.get("target_entity_id")

        # Validate entities exist
        for entity_id, role in [(source_id, "source"), (target_id, "target")]:
            entity = await self.session.execute(
                select(GraphEntity).where(
                    GraphEntity.id == entity_id,
                    GraphEntity.user_id == user_id,
                )
            )
            if not entity.scalar_one_or_none():
                raise ResourceNotFoundError(
                    resource=f"{role.capitalize()} entity",
                    identifier=str(entity_id)
                )

        # Validate source != target
        if source_id == target_id:
            from ..core.exceptions import BusinessLogicError
            raise BusinessLogicError(
                message="Cannot create a relation from an entity to itself",
                error_code="SELF_REFERENCE",
            )

        relation = GraphRelation(
            document_id=document_id,
            user_id=user_id,
            **relation_data
        )
        self.session.add(relation)
        await self.session.flush()
        await self.session.refresh(relation)
        return relation

    async def delete_relation(
        self,
        relation_id: uuid.UUID,
        expected_version: int,
        user_id: uuid.UUID,
    ) -> bool:
        """
        Delete a relation with optimistic concurrency check.
        """
        stmt = (
            delete(GraphRelation)
            .where(
                GraphRelation.id == relation_id,
                GraphRelation.user_id == user_id,
                GraphRelation.version == expected_version,
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount == 0:
            existing = await self.session.execute(
                select(GraphRelation).where(
                    GraphRelation.id == relation_id,
                    GraphRelation.user_id == user_id,
                )
            )
            existing_relation = existing.scalar_one_or_none()
            if existing_relation:
                raise DuplicateResourceError(
                    message="Edit conflict: relation was modified by another user",
                    details={"current_version": existing_relation.version, "expected_version": expected_version}
                )
            raise ResourceNotFoundError(
                resource="Relation",
                identifier=str(relation_id)
            )

        return True

    # =========================================================================
    # Audit Logging
    # =========================================================================

    async def log_edit(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        entity_type: str,
        document_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
        relation_id: Optional[uuid.UUID] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Async fire-and-forget audit log entry.
        If logging fails, log warning but do NOT fail the main operation.
        """
        try:
            log_entry = GraphEditLog(
                user_id=user_id,
                document_id=document_id,
                entity_id=entity_id,
                relation_id=relation_id,
                action=action,
                entity_type=entity_type,
                old_value=old_value,
                new_value=new_value,
            )
            self.session.add(log_entry)
            # Do NOT flush here — let the main transaction handle it.
            # If the main operation commits, this log will be committed too.
            # If the main operation rolls back, this log rolls back too.
        except Exception as e:
            logger.warning(f"Failed to log graph edit (non-critical): {e}")
