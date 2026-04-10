import pytest
from app.core.fast_extractor import FastExtractor
from app.schemas.lightrag import ExtractionResult

def test_fast_extractor_singleton():
    """Kiểm tra FastExtractor là một Singleton."""
    # Note: Đây có thể fail nếu không có spacy model
    try:
        ext1 = FastExtractor()
        ext2 = FastExtractor()
        assert ext1 is ext2
    except RuntimeError:
        pytest.skip("spaCy model 'en_core_web_sm' not found")

def test_fast_extractor_basic():
    """Kiểm tra khả năng trích xuất cơ bản của spaCy."""
    try:
        extractor = FastExtractor()
        text = "Apple is looking at buying U.K. startup for $1 billion. Steve Jobs founded Apple."
        result = extractor.extract(text)
        
        assert isinstance(result, ExtractionResult)
        assert len(result.entities) > 0
        
        # Kiểm tra types (đã qua mapping)
        entity_names = [e.name for e in result.entities]
        entity_types = [e.entity_type for e in result.entities]
        
        assert "Apple" in entity_names
        assert "Organization" in entity_types or "ORGANIZATION" in entity_types
        
        # Quan hệ nên rỗng trong spaCy extractor
        assert len(result.relations) == 0
    except RuntimeError:
        pytest.skip("spaCy model 'en_core_web_sm' not found")
