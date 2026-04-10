import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.entity_extractor import EntityExtractor
from app.schemas.lightrag import ExtractionResult, ExtractedEntity, EntityRelation

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.ENTITY_EXTRACTION_METHOD = "hybrid"
    return config

@pytest.fixture
def mock_fast_extractor():
    with patch("app.core.fast_extractor.FastExtractor") as mock:
        instance = mock.return_value
        instance.extract.return_value = ExtractionResult(
            entities=[
                ExtractedEntity(name="Apple", entity_type="ORGANIZATION", description="Fast desc", confidence=0.8)
            ],
            relations=[]
        )
        yield instance


@pytest.mark.asyncio
async def test_merge_results():
    """Kiểm tra thuật toán merge kết quả spaCy và LLM."""
    extractor = EntityExtractor()
    
    fast = ExtractionResult(
        entities=[
            ExtractedEntity(name="Apple", entity_type="ORGANIZATION", description="Fast desc", confidence=0.8),
            ExtractedEntity(name="Google", entity_type="ORGANIZATION", description="Only in fast", confidence=0.7)
        ],
        relations=[]
    )
    
    llm = ExtractionResult(
        entities=[
            ExtractedEntity(name="Apple", entity_type="TECHNOLOGY", description="LLM better desc", confidence=0.9),
            ExtractedEntity(name="Microsoft", entity_type="ORGANIZATION", description="Only in LLM", confidence=0.85)
        ],
        relations=[
            EntityRelation(source="Apple", target="Microsoft", relation_type="COMPETES_WITH", description="Competition")
        ]
    )
    
    merged = extractor._merge_results(fast, llm)
    
    # Check entities
    names = {e.name: e for e in merged.entities}
    assert "Apple" in names
    assert names["Apple"].entity_type == "TECHNOLOGY"  # Ưu tiên LLM type
    assert names["Apple"].description == "LLM better desc"  # Ưu tiên LLM desc
    assert names["Apple"].confidence == 0.9  # Max confidence
    
    assert "Google" in names  # Keep fast-only
    assert "Microsoft" in names  # Keep llm-only
    
    # Check relations
    assert len(merged.relations) == 1
    assert merged.relations[0].source == "Apple"

@pytest.mark.asyncio
async def test_hybrid_extraction_early_exit(mock_config, mock_fast_extractor):
    """Kiểm tra hybrid trích xuất dừng sớm khi đủ thực thể."""
    with patch("app.core.entity_extractor.llm_service") as mock_llm:
        # Mock LLM returns some entities
        mock_llm.structured_extraction = AsyncMock(return_value=ExtractionResult(
            entities=[ExtractedEntity(name=f"Entity {i}", entity_type="CONCEPT", description="desc", confidence=0.9) for i in range(40)],
            relations=[]
        ))
        
        extractor = EntityExtractor(config=mock_config)
        chunks = ["chunk1", "chunk2", "chunk3", "chunk4", "chunk5", "chunk6", "chunk7", "chunk8", "chunk9", "chunk10"]
        
        # Threshold là 30. LLM batch 1 trả về 40 thực thể -> Dừng ngay.
        result = await extractor.extract(chunks)
        
        assert len(result.entities) >= 30
        # Kiểm tra llm_service chỉ được gọi 1 lần (Batch mandatory #1)
        assert mock_llm.structured_extraction.call_count == 1

@pytest.mark.asyncio
async def test_hybrid_extraction_fallback(mock_config, mock_fast_extractor):
    """Kiểm tra hybrid trích xuất gọi thêm batch nếu thiếu thực thể."""
    with patch("app.core.entity_extractor.llm_service") as mock_llm:
        # Mock LLM trả về ít thực thể mỗi lần
        mock_llm.structured_extraction = AsyncMock(return_value=ExtractionResult(
            entities=[ExtractedEntity(name="New Ent", entity_type="CONCEPT", description="desc", confidence=0.9)],
            relations=[]
        ))
        
        extractor = EntityExtractor(config=mock_config)
        # Giả định spaCy trích xuất được 1 thực thể (từ mock_fast_extractor)
        # LLM batch 1 thêm 1 thực thể -> tổng 2 < 30 -> Tiếp tục loop
        
        chunks = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"] # 2 batches (size 5)
        
        result = await extractor.extract(chunks)
        
        # Phải gọi LLM 2 lần (batch 1 mandatory + batch 2 fallback)
        assert mock_llm.structured_extraction.call_count == 2
