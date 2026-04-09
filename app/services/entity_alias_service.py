"""
EntityAliasResolutionService - Cross-document entity alias resolution.

Resolves entity aliases across documents:
- "AI" → "Artificial Intelligence"
- "ML" → "Machine Learning"
- "LLM" → "Large Language Model"

Uses similarity matching + LLM verification + user confirmation.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.graph import GraphEntity, EntityAlias
from app.services.llm_service import llm_service
from app.constants import ENTITY_ALIAS_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


class EntityAliasResolutionService:
    """
    Service for resolvinging entity aliases across documents.

    Provides:
    - Alias detection via fuzzy matching
    - LLM-powered alias verification
    - Alias creation with user confirmation
    - Alias lookup (alias_name → canonical_name)
    - Global entity aggregation across documents
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_entity_alias(
        self,
        entity_name: str,
        user_id: uuid.UUID,
        suggested_canonical: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve an entity alias to its canonical name.

        Args:
            entity_name: The entity name/alias to resolve
            user_id: User UUID for filtering
            suggested_canonical: Optional suggested canonical name (skip detection if provided)

        Returns:
            Canonical entity name if found, None otherwise
        """
        # 1. Check existing aliases first
        existing_alias = await self._lookup_alias(entity_name, user_id)
        if existing_alias:
            return existing_alias.canonical_name

        # 2. Fuzzy match with existing entities
        if not suggested_canonical:
            suggested_canonical = await self._fuzzy_match_entity(
                entity_name, user_id
            )

        # 3. LLM verification if suggested
        if suggested_canonical:
            is_valid = await self._verify_alias_with_llm(
                entity_name, suggested_canonical
            )
            if is_valid:
                return suggested_canonical

        return None

    async def suggest_aliases(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Suggest potential entity aliases for user review.

        Finds entities with similar names across documents
        that might be aliases of the same concept.

        Returns:
            List of dicts with:
            - alias_name: str
            - suggested_canonical: str
            - confidence: float
            - occurrences: int (how many docs use this alias)
        """
        # Get all unique entity names for user
        stmt = (
            select(GraphEntity.canonical_name, func.count(GraphEntity.id).label('occurrences'))
            .where(GraphEntity.user_id == user_id)
            .group_by(GraphEntity.canonical_name)
            .order_by(func.count(GraphEntity.id).desc())
            .limit(limit * 3)  # Get more for filtering
        )
        result = await self.session.execute(stmt)
        entities = result.all()

        entity_names = [e.canonical_name for e in entities]
        suggestions = []

        # Compare pairs of entity names
        for i, name1 in enumerate(entity_names):
            for name2 in entity_names[i+1:]:
                similarity = self._calculate_similarity(name1, name2)
                
                if similarity >= ENTITY_ALIAS_SIMILARITY_THRESHOLD:
                    # Determine which is canonical (longer name usually more complete)
                    if len(name1) >= len(name2):
                        canonical, alias = name1, name2
                    else:
                        canonical, alias = name2, name1

                    # Check if alias already exists
                    exists = await self._alias_exists(alias, canonical, user_id)
                    if not exists:
                        suggestions.append({
                            "alias_name": alias,
                            "suggested_canonical": canonical,
                            "confidence": round(similarity, 3),
                            "occurrences": next(
                                (e.occurrences for e in entities if e.canonical_name == alias), 0
                            ),
                        })

        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:limit]

    async def create_alias(
        self,
        user_id: uuid.UUID,
        alias_name: str,
        canonical_name: str,
        confidence: float = 1.0,
        source: str = "manual",
    ) -> Optional[EntityAlias]:
        """
        Create an entity alias mapping.

        Args:
            user_id: User UUID
            alias_name: The alias to create
            canonical_name: The canonical entity name
            confidence: Confidence score (0-1)
            source: "manual" (user confirmed) | "ai_suggested" | "auto"

        Returns:
            Created EntityAlias or None if already exists
        """
        # Check if alias already exists
        existing = await self._lookup_alias(alias_name, user_id)
        if existing:
            logger.info(f"Alias '{alias_name}' already exists → '{existing.canonical_name}'")
            return existing

        # Verify alias and canonical entities exist
        canonical_exists = await self._entity_exists(canonical_name, user_id)
        if not canonical_exists:
            logger.warning(f"Canonical entity '{canonical_name}' does not exist")
            return None

        # Create alias
        alias = EntityAlias(
            user_id=user_id,
            alias_name=alias_name,
            canonical_name=canonical_name,
            confidence=confidence,
            source=source,
        )
        self.session.add(alias)
        await self.session.flush()

        logger.info(f"Created alias: '{alias_name}' → '{canonical_name}' (source={source})")
        return alias

    async def bulk_create_aliases(
        self,
        user_id: uuid.UUID,
        aliases: List[Dict[str, Any]],
    ) -> int:
        """
        Bulk create aliases from suggestions.

        Args:
            user_id: User UUID
            aliases: List of dicts with keys: alias_name, canonical_name, confidence, source

        Returns:
            Number of aliases created
        """
        created_count = 0
        for alias_data in aliases:
            result = await self.create_alias(
                user_id=user_id,
                alias_name=alias_data["alias_name"],
                canonical_name=alias_data["canonical_name"],
                confidence=alias_data.get("confidence", 1.0),
                source=alias_data.get("source", "manual"),
            )
            if result:
                created_count += 1

        return created_count

    async def get_user_aliases(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[EntityAlias]:
        """Get all aliases for a user."""
        stmt = (
            select(EntityAlias)
            .where(EntityAlias.user_id == user_id)
            .order_by(EntityAlias.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_alias(
        self,
        user_id: uuid.UUID,
        alias_name: str,
    ) -> bool:
        """Delete an entity alias."""
        alias = await self._lookup_alias(alias_name, user_id)
        if not alias:
            return False

        await self.session.delete(alias)
        await self.session.flush()
        return True

    async def get_global_entities(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated entities across all user's documents.

        Groups entities by canonical_name and returns:
        - canonical_name
        - entity_type
        - document_count (how many docs mention this entity)
        - avg_confidence
        - total_occurrences
        """
        stmt = (
            select(
                GraphEntity.canonical_name,
                GraphEntity.entity_type,
                func.count(GraphEntity.id).label('total_occurrences'),
                func.count(func.distinct(GraphEntity.document_id)).label('document_count'),
                func.avg(GraphEntity.confidence).label('avg_confidence'),
            )
            .where(GraphEntity.user_id == user_id)
            .group_by(
                GraphEntity.canonical_name,
                GraphEntity.entity_type,
            )
            .order_by(func.count(GraphEntity.id).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "canonical_name": row.canonical_name,
                "entity_type": row.entity_type,
                "total_occurrences": row.total_occurrences,
                "document_count": row.document_count,
                "avg_confidence": round(float(row.avg_confidence), 3),
            }
            for row in rows
        ]

    # ========== Private Methods ==========

    async def _lookup_alias(
        self,
        alias_name: str,
        user_id: uuid.UUID,
    ) -> Optional[EntityAlias]:
        """Look up an alias in the database."""
        stmt = (
            select(EntityAlias)
            .where(
                EntityAlias.user_id == user_id,
                EntityAlias.alias_name == alias_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _alias_exists(
        self,
        alias_name: str,
        canonical_name: str,
        user_id: uuid.UUID,
    ) -> bool:
        """Check if alias already exists."""
        stmt = (
            select(EntityAlias)
            .where(
                EntityAlias.user_id == user_id,
                EntityAlias.alias_name == alias_name,
                EntityAlias.canonical_name == canonical_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def _entity_exists(
        self,
        entity_name: str,
        user_id: uuid.UUID,
    ) -> bool:
        """Check if canonical entity exists."""
        stmt = (
            select(GraphEntity)
            .where(
                GraphEntity.user_id == user_id,
                GraphEntity.canonical_name == entity_name,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def _fuzzy_match_entity(
        self,
        entity_name: str,
        user_id: uuid.UUID,
        threshold: float = ENTITY_ALIAS_SIMILARITY_THRESHOLD,
    ) -> Optional[str]:
        """
        Fuzzy match entity name with existing entities.
        Returns canonical_name if match found, None otherwise.
        """
        # Get all unique canonical names
        stmt = (
            select(GraphEntity.canonical_name)
            .where(GraphEntity.user_id == user_id)
            .distinct()
        )
        result = await self.session.execute(stmt)
        canonical_names = [row.canonical_name for row in result.all()]

        # Fuzzy match
        best_match = None
        best_score = 0.0

        for canonical in canonical_names:
            score = self._calculate_similarity(entity_name, canonical)
            if score > best_score:
                best_score = score
                best_match = canonical

        if best_score >= threshold:
            return best_match

        return None

    def _calculate_similarity(
        self,
        name1: str,
        name2: str,
    ) -> float:
        """
        Calculate similarity between two entity names.
        Uses SequenceMatcher for fuzzy matching.
        Also checks if one name is substring of another.
        """
        # Normalize
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # Exact match
        if n1 == n2:
            return 1.0

        # Substring check (e.g., "AI" in "Artificial Intelligence")
        if n1 in n2 or n2 in n1:
            return max(0.9, len(n1) / len(n2) if len(n1) < len(n2) else len(n2) / len(n1))

        # SequenceMatcher fuzzy ratio
        return SequenceMatcher(None, n1, n2).ratio()

    async def _verify_alias_with_llm(
        self,
        alias_name: str,
        canonical_name: str,
    ) -> bool:
        """
        Use LLM to verify if alias_name refers to canonical_name.
        Returns True if LLM confirms, False otherwise.
        """
        prompt = f"""Does "{alias_name}" refer to the same concept as "{canonical_name}"?

Examples:
- "AI" → "Artificial Intelligence": YES
- "ML" → "Machine Learning": YES
- "Python" → "Programming Language": YES
- "Apple" → "Fruit": NO (could be company vs fruit)
- "Java" → "Coffee": NO (could be island vs coffee)

Return ONLY "YES" or "NO", no explanation."""

        try:
            response = await llm_service.get_chat_completion([
                {"role": "user", "content": prompt}
            ])
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
        except Exception as e:
            logger.warning(f"LLM alias verification failed: {e}")
            return False  # Conservative: don't create alias if uncertain


# Singleton factory function (requires session)
def get_alias_resolution_service(session: AsyncSession) -> EntityAliasResolutionService:
    """Get EntityAliasResolutionService instance."""
    return EntityAliasResolutionService(session)
