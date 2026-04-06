from typing import List, Dict, Any, Optional
from ..services.llm_service import llm_service
from ..schemas.lightrag import ExtractionResult, ExtractedEntity
import json

class EntityExtractor:
    """
    Service responsible for extracting entities and relationships from text.
    Leverages LLMs via JSON mode and rule-based methods.
    """
    
    def __init__(self, aliases: dict = None):
        self.aliases = aliases or {}

    def _normalize_name(self, name: str) -> str:
        clean_name = name.strip().lower()
        if clean_name in self.aliases:
            return self.aliases[clean_name]
        return name.strip().title()

    async def extract(self, text: str) -> Optional[ExtractionResult]:
        """
        Input: Plain text
        Output: ExtractionResult containing entities and relationships.
        """
        prompt = f"""
        Extract key entities and their relationships from the text below.
        Focus on important technical concepts, people, and organizations.
        Output MUST be a JSON object with:
        - "entities": list of objects with "name", "entity_type", "description", "confidence"
        - "relations": list of objects with "source", "target", "relation_type", "description"

        Text:
        {text}
        """
        result = await llm_service.structured_extraction(prompt, ExtractionResult)
        
        if result:
            # Normalize names and confidence
            for entity in result.entities:
                entity.name = self._normalize_name(entity.name)
                # Normalize confidence if model returns 0-100
                if entity.confidence > 1.0:
                    entity.confidence = entity.confidence / 100.0

            for relation in result.relations:
                relation.source = self._normalize_name(relation.source)
                relation.target = self._normalize_name(relation.target)
        
        return result

    def deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Map-Reduce: Merge entities with the same canonical name.
        Keep longest description and highest confidence.
        """
        merged: Dict[str, ExtractedEntity] = {}
        for entity in entities:
            name = entity.name
            if name not in merged:
                merged[name] = entity
            else:
                # Compare and take best attributes
                if len(entity.description) > len(merged[name].description):
                    merged[name].description = entity.description
                if entity.confidence > merged[name].confidence:
                    merged[name].confidence = entity.confidence
        
        return list(merged.values())
