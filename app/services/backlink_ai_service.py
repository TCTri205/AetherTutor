"""
BacklinkAIService for Stage 2 - Zettelkasten & Bi-directional Linking

AI service to suggest backlinks between notes and related graph entities.
"""

import uuid
import json
import logging
import asyncio
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.llm_service import LLMService
from app.repositories.note_repo import NoteRepository, NoteLinkRepository
from app.repositories.graph_repo import GraphRepository
from app.constants import (
    NOTE_LINK_SUGGESTION_THRESHOLD,
    BACKLINK_AI_MODEL_MAX_TOKENS
)

logger = logging.getLogger(__name__)


class RelatedEntitySuggestion(BaseModel):
    """Suggestion for a related graph entity."""
    entity_id: uuid.UUID
    entity_name: str
    relation_type: str = Field(description="How this entity relates to the note")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    context: str = Field(description="Why this entity is related")


class RelatedNoteSuggestion(BaseModel):
    """Suggestion for a related note."""
    note_id: uuid.UUID
    note_title: str
    relation_type: str = Field(description="How this note relates to the source note")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    context: str = Field(description="Why this note is related")


class BacklinkSuggestionsResponse(BaseModel):
    """Response containing suggested backlinks and related entities."""
    related_entities: List[RelatedEntitySuggestion] = []
    related_notes: List[RelatedNoteSuggestion] = []


class BacklinkAIService:
    """
    AI service for suggesting backlinks and related entities.
    
    Uses LLM to analyze note content and find connections to:
    1. Graph entities from knowledge graph
    2. Other notes in the Zettelkasten
    """

    def __init__(
        self,
        llm_service: LLMService,
        note_repo: NoteRepository,
        note_link_repo: NoteLinkRepository,
        graph_repo: GraphRepository,
    ):
        self.llm_service = llm_service
        self.note_repo = note_repo
        self.note_link_repo = note_link_repo
        self.graph_repo = graph_repo

    async def find_related_entities(
        self,
        note_content: str,
        user_id: uuid.UUID,
        top_k: int = 5,
    ) -> List[RelatedEntitySuggestion]:
        """
        Find graph entities related to note content.

        Uses LLM to identify candidate entity names, then looks up
        actual entity IDs from the user's knowledge graph.
        """
        prompt = f"""
Analyze the following note content and identify the key concepts/entities that might relate to a knowledge graph.

Note content:
{note_content}

Return a JSON list of entities (max {top_k}) with:
- entity_name: The concept/entity name
- relation_type: How it relates to the note (e.g., "mentions", "defines", "applies", "contrasts_with")
- confidence: How confident you are (0.0-1.0)
- context: Brief explanation of why this entity relates to the note

Format as JSON array only. No markdown, no explanation.
"""

        try:
            response = await self.llm_service.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI that analyzes notes and identifies related knowledge graph entities. "
                            "Output ONLY valid JSON arrays."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=BACKLINK_AI_MODEL_MAX_TOKENS,
            )

            content = response.choices[0].message.content or "[]"
            suggestions_data = json.loads(content)

            # Extract entity names for lookup
            entity_names = [item.get("entity_name", "") for item in suggestions_data if item.get("entity_name")]

            # Lookup actual entity IDs from the knowledge graph
            name_to_entity = await self.graph_repo.get_entities_by_names(user_id, entity_names)

            suggestions = []
            for item in suggestions_data[:top_k]:
                entity_name = item.get("entity_name", "")
                confidence = item.get("confidence", 0)

                if confidence < NOTE_LINK_SUGGESTION_THRESHOLD:
                    continue

                # Only include entities that actually exist in the user's graph
                matched_entity = name_to_entity.get(entity_name)
                if not matched_entity:
                    logger.debug(f"Entity '{entity_name}' not found in user's graph, skipping")
                    continue

                suggestions.append(RelatedEntitySuggestion(
                    entity_id=matched_entity.id,
                    entity_name=matched_entity.canonical_name,
                    relation_type=item.get("relation_type", "related_to"),
                    confidence=confidence,
                    context=item.get("context", ""),
                ))

            return suggestions[:top_k]

        except Exception as e:
            logger.error(f"Error finding related entities: {e}")
            return []

    async def find_related_notes(
        self,
        note_content: str,
        note_title: str,
        user_id: uuid.UUID,
        exclude_note_id: Optional[uuid.UUID] = None,
        top_k: int = 3,
    ) -> List[RelatedNoteSuggestion]:
        """
        Find other notes that are semantically related.
        
        Uses LLM to analyze content overlap and thematic connections.
        """
        # Get candidate notes (recent notes excluding current)
        candidate_notes = await self.note_repo.get_notes_for_backlink_suggestion(
            user_id=user_id,
            exclude_note_id=exclude_note_id or uuid.UUID(int=0),
            limit=20,
        )
        
        if not candidate_notes:
            return []
        
        # Build context of candidate notes
        notes_context = "\n".join([
            f"- Title: {n.title}\n  Content preview: {n.content[:200]}..."
            for n in candidate_notes[:10]  # Limit to avoid huge prompts
        ])
        
        prompt = f"""
Given a source note and a list of other notes, identify which notes are thematically related.

Source note:
Title: {note_title}
Content: {note_content[:1000]}

Other notes:
{notes_context}

Return a JSON list of max {top_k} related notes with:
- note_title: Title of the related note (must match exactly from the list above)
- relation_type: How they relate (e.g., "extends", "contrasts", "prerequisite", "example_of", "related_concept")
- confidence: How strong the connection is (0.0-1.0)
- context: Brief explanation of the relationship

Format as JSON array only. No markdown, no explanation.
"""

        try:
            response = await self.llm_service.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI that finds connections between notes in a Zettelkasten system. "
                            "Output ONLY valid JSON arrays."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=BACKLINK_AI_MODEL_MAX_TOKENS,
            )
            
            content = response.choices[0].message.content or "[]"
            suggestions_data = json.loads(content)
            
            # Build lookup map
            note_by_title = {n.title: n for n in candidate_notes}
            
            suggestions = []
            for item in suggestions_data:
                note_title_match = item.get("note_title", "")
                if note_title_match in note_by_title:
                    note = note_by_title[note_title_match]
                    confidence = item.get("confidence", 0)
                    
                    if confidence >= NOTE_LINK_SUGGESTION_THRESHOLD:
                        suggestions.append(RelatedNoteSuggestion(
                            note_id=note.id,
                            note_title=note.title,
                            relation_type=item.get("relation_type", "related_to"),
                            confidence=confidence,
                            context=item.get("context", ""),
                        ))
            
            return suggestions[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding related notes: {e}")
            return []

    async def suggest_backlinks_for_note(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> BacklinkSuggestionsResponse:
        """
        Get all backlink suggestions for a note (entities + related notes).
        """
        note = await self.note_repo.get(note_id)
        if not note or note.user_id != user_id:
            return BacklinkSuggestionsResponse()
        
        # Run both searches in parallel
        entities_task = self.find_related_entities(
            note_content=note.content,
            user_id=user_id,
            top_k=5,
        )
        
        notes_task = self.find_related_notes(
            note_content=note.content,
            note_title=note.title,
            user_id=user_id,
            exclude_note_id=note_id,
            top_k=3,
        )
        
        related_entities, related_notes = await asyncio.gather(
            entities_task, notes_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(related_entities, Exception):
            logger.error(f"Entity suggestion failed: {related_entities}")
            related_entities = []
        if isinstance(related_notes, Exception):
            logger.error(f"Note suggestion failed: {related_notes}")
            related_notes = []
        
        return BacklinkSuggestionsResponse(
            related_entities=related_entities if isinstance(related_entities, list) else [],
            related_notes=related_notes if isinstance(related_notes, list) else [],
        )
