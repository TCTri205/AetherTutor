import uuid
import logging
from typing import List, Dict, Any
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.graph import GraphEntity
from ..repositories.graph_repo import GraphRepository
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class EntityResolutionService:
    """
    Service to resolve and merge entities from different sources (AI-extracted vs Obsidian-imported).
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GraphRepository(db)

    async def resolve_and_merge(self, user_id: uuid.UUID, new_entity: Dict[str, Any], fuzzy_threshold: float = 0.9) -> GraphEntity:
        """
        Check if an entity with same/similar name exists for the user.
        If yes, merge them prioritizing Manual > Obsidian > AI.
        """
        canonical_name = new_entity["canonical_name"]
        
        # 1. Exact match lookup
        stmt = (
            select(GraphEntity)
            .where(
                GraphEntity.user_id == user_id,
                GraphEntity.canonical_name == canonical_name
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            # 2. Fuzzy match lookup
            # Find all entities for user and check similarity
            stmt = select(GraphEntity).where(GraphEntity.user_id == user_id)
            result = await self.db.execute(stmt)
            all_entities = result.scalars().all()
            
            for ent in all_entities:
                score = SequenceMatcher(None, canonical_name.lower(), ent.canonical_name.lower()).ratio()
                if score >= fuzzy_threshold:
                    # High enough similarity to suggest it might be the same
                    # Use LLM to verify if it's actually the same concept
                    is_same = await self.llm_verify_merge(new_entity, {
                        "canonical_name": ent.canonical_name,
                        "entity_type": ent.entity_type,
                        "description": ent.description
                    })
                    if is_same:
                        existing = ent
                        break

        if not existing:
            return await self.repo.upsert_entity(user_id, None, new_entity)

        # 3. Merge logic
        # Manual > Obsidian > AI
        source_priority = {"manual": 3, "obsidian_import": 2, "ai_extracted": 1, "merged": 4}
        
        old_priority = source_priority.get(existing.source, 0)
        new_priority = source_priority.get(new_entity.get("source"), 0)
        
        merged_data = {
            "canonical_name": existing.canonical_name,
            "entity_type": existing.entity_type if old_priority >= new_priority else new_entity.get("entity_type"),
            "description": self._merge_descriptions(existing.description, new_entity.get("description", "")),
            "confidence": max(existing.confidence, new_entity.get("confidence", 0.0)),
            "source": "merged" if old_priority != new_priority else existing.source,
            "tags": list(set((existing.tags or []) + (new_entity.get("tags") or []))),
            "file_path": existing.file_path or new_entity.get("file_path"),
            "metadata": {**(existing.metadata_ or {}), **(new_entity.get("metadata") or {})}
        }
        
        # Update existing entity
        for key, value in merged_data.items():
            if key == "metadata":
                setattr(existing, "metadata_", value)
            else:
                setattr(existing, key, value)
        
        await self.db.flush()
        return existing

    async def llm_verify_merge(self, ent1: Dict[str, Any], ent2: Dict[str, Any]) -> bool:
        """Use LLM to verify if two entities represent the same real-world concept."""
        from pydantic import BaseModel
        
        class MergeVerification(BaseModel):
            is_same: bool
            reason: str

        prompt = f"""Phân tích xem hai thực thể sau có cùng biểu thị một khái niệm/thực thể thực tế hay không:

Thực thể 1:
- Tên: {ent1['canonical_name']}
- Loại: {ent1.get('entity_type', 'N/A')}
- Mô tả: {ent1.get('description', 'N/A')}

Thực thể 2:
- Tên: {ent2['canonical_name']}
- Loại: {ent2.get('entity_type', 'N/A')}
- Mô tả: {ent2.get('description', 'N/A')}

Trả về JSON:
{{
  "is_same": true|false,
  "reason": "Giải thích ngắn gọn"
}}
"""
        try:
            result = await llm_service.structured_extraction(prompt, MergeVerification)
            return result.is_same if result else False
        except Exception as e:
            logger.error(f"Error in LLM merge verification: {e}")
            return False

    def _merge_descriptions(self, desc1: str, desc2: str) -> str:
        """Merge descriptions by keeping the longer and more informative one or combining them."""
        if not desc1: return desc2
        if not desc2: return desc1
        if desc1 == desc2: return desc1
        
        # Simple heuristic: take the longer one
        return desc1 if len(desc1) >= len(desc2) else desc2

    async def get_potential_duplicates(self, user_id: uuid.UUID, threshold: float = 0.85) -> List[Dict[str, Any]]:
        """Find entities with similar names that might be duplicates."""
        stmt = select(GraphEntity).where(GraphEntity.user_id == user_id)
        result = await self.db.execute(stmt)
        entities = result.scalars().all()
        
        duplicates = []
        names = [e.canonical_name for e in entities]
        
        for i, name1 in enumerate(names):
            for j, name2 in enumerate(names[i+1:]):
                score = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
                if score >= threshold:
                    duplicates.append({
                        "entity1": {"id": str(entities[i].id), "name": name1},
                        "entity2": {"id": str(entities[i+j+1].id), "name": name2},
                        "score": round(score, 3)
                    })
        return duplicates

    async def merge_entities(self, user_id: uuid.UUID, primary_id: uuid.UUID, secondary_id: uuid.UUID) -> GraphEntity:
        """
        Gộp thực thể 'secondary' vào 'primary'.
        Toàn bộ quan hệ của secondary sẽ được chuyển sang primary.
        """
        # 1. Fetch both entities
        stmt = select(GraphEntity).where(
            GraphEntity.id.in_([primary_id, secondary_id]),
            GraphEntity.user_id == user_id
        )
        res = await self.db.execute(stmt)
        entities = res.scalars().all()
        
        if len(entities) < 2:
            raise ValueError("Một hoặc cả hai thực thể không tồn tại hoặc không thuộc quyền sở hữu của người dùng.")
        
        # Identify which is which
        primary = next(e for e in entities if e.id == primary_id)
        secondary = next(e for e in entities if e.id == secondary_id)

        # 2. Migrate Relations
        await self.repo.migrate_relations(secondary.id, primary.id)

        # 3. Merge Data
        source_priority = {"manual": 3, "obsidian_import": 2, "ai_extracted": 1, "merged": 4}
        old_priority = source_priority.get(primary.source, 0)
        new_priority = source_priority.get(secondary.source, 0)

        primary.description = self._merge_descriptions(primary.description, secondary.description)
        primary.confidence = max(primary.confidence, secondary.confidence)
        primary.tags = list(set((primary.tags or []) + (secondary.tags or [])))
        primary.metadata_ = {**(secondary.metadata_ or {}), **(primary.metadata_ or {})}
        
        if old_priority != new_priority:
            primary.source = "merged"

        # 4. Delete Secondary
        await self.db.delete(secondary)
        
        await self.db.flush()
        return primary
