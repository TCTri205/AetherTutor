"""
Fast Entity Extractor — spaCy
Dùng để extract entities NHANH (không cần LLM).
"""
import spacy
import threading
import logging
from typing import List
from ..schemas.lightrag import ExtractedEntity, ExtractionResult

logger = logging.getLogger(__name__)

# Map spaCy NER labels → hệ thống entity types chuẩn
# References: https://spacy.io/models/en#en_core_web_sm
SPACY_TO_STANDARD_TYPES = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "PRODUCT": "TECHNOLOGY",
    "WORK_OF_ART": "CONCEPT",
    "EVENT": "EVENT",
    "LAW": "CONCEPT",
    "LANGUAGE": "CONCEPT",
    "NORP": "CONCEPT",
    "FAC": "LOCATION",
    "MONEY": "CONCEPT",
    "QUANTITY": "CONCEPT",
    "DATE": "CONCEPT",
    "TIME": "CONCEPT",
    "PERCENT": "CONCEPT",
    "ORDINAL": "CONCEPT",
    "CARDINAL": "CONCEPT",
}

class FastExtractor:
    """Thread-safe Singleton cho Model spaCy (~50MB)"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                try:
                    # Tải model spaCy. Yêu cầu: python -m spacy download en_core_web_sm
                    cls._instance._nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model 'en_core_web_sm' loaded successfully")
                except OSError as e:
                    logger.error(
                        "spaCy model 'en_core_web_sm' not found. "
                        "Install with: python -m spacy download en_core_web_sm"
                    )
                    raise RuntimeError(
                        "spaCy model required for FastExtractor is missing. "
                        "Run: python -m spacy download en_core_web_sm"
                    ) from e
        return cls._instance

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities từ text bằng spaCy.
        
        Args:
            text: Văn bản thuần túy.
            
        Returns:
            ExtractionResult (relations sẽ rỗng vì spaCy NER không trích xuất quan hệ phức tạp tốt).
        """
        doc = self._nlp(text)

        entities = []
        for ent in doc.ents:
            standard_type = SPACY_TO_STANDARD_TYPES.get(ent.label_, "CONCEPT")
            entities.append(ExtractedEntity(
                name=ent.text.strip().title(),
                entity_type=standard_type,
                description=f"{ent.label_} entity extracted from context",
                confidence=0.8
            ))

        # spaCy NER không trích xuất relations tự động cho technical docs
        relations = []

        return ExtractionResult(entities=entities, relations=relations)
