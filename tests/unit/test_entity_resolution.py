import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.entity_resolution_service import EntityResolutionService
from app.models.graph import GraphEntity

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def resolution_service(mock_db):
    return EntityResolutionService(mock_db)

class TestEntityResolutionService:
    
    @pytest.mark.asyncio
    async def test_resolve_exact_match_merge(self, resolution_service, mock_db):
        """Test merging entities with exact name match."""
        user_id = uuid.uuid4()
        existing_entity = MagicMock(spec=GraphEntity)
        existing_entity.canonical_name = "Python"
        existing_entity.entity_type = "concept"
        existing_entity.description = "Old description"
        existing_entity.source = "ai_extracted"
        existing_entity.confidence = 0.5
        existing_entity.tags = ["ai"]
        existing_entity.file_path = None
        existing_entity.metadata_ = {}

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_entity
        mock_db.execute.return_value = mock_result

        new_entity_data = {
            "canonical_name": "Python",
            "entity_type": "programming_language",
            "description": "A very long and descriptive text about Python programming language.",
            "source": "obsidian_import",
            "confidence": 1.0,
            "tags": ["programming", "backend"],
            "file_path": "/vault/python.md",
            "metadata": {"author": "Guido"}
        }

        result = await resolution_service.resolve_and_merge(user_id, new_entity_data)

        assert result == existing_entity
        # Check if merged
        assert existing_entity.entity_type == "programming_language"  # Priority: obsidian > ai
        assert existing_entity.source == "merged"
        assert existing_entity.confidence == 1.0
        assert set(existing_entity.tags) == {"ai", "programming", "backend"}
        assert existing_entity.file_path == "/vault/python.md"

    async def test_resolve_no_match_creates_new(self, resolution_service, mock_db):
        """Test creating new entity when no match found."""
        user_id = uuid.uuid4()
        
        # Mock query result (no match)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        new_entity_data = {
            "canonical_name": "New Concept",
            "entity_type": "note",
            "description": "Something new"
        }

        with patch.object(resolution_service.repo, 'upsert_entity', new_callable=AsyncMock) as mock_upsert:
            mock_upsert.return_value = MagicMock(spec=GraphEntity)
            await resolution_service.resolve_and_merge(user_id, new_entity_data)
            mock_upsert.assert_called_once()

    def test_merge_descriptions(self, resolution_service):
        """Test description merging logic (longer one wins)."""
        desc_short = "Short desc"
        desc_long = "This is a much longer and more informative description of the same thing."
        
        assert resolution_service._merge_descriptions(desc_short, desc_long) == desc_long
        assert resolution_service._merge_descriptions(desc_long, desc_short) == desc_long
        assert resolution_service._merge_descriptions("", "Something") == "Something"

    async def test_get_potential_duplicates(self, resolution_service, mock_db):
        """Test fuzzy matching for duplicates."""
        user_id = uuid.uuid4()
        e1 = MagicMock(spec=GraphEntity)
        e1.canonical_name = "Artificial Intelligence"
        e1.id = uuid.uuid4()
        
        e2 = MagicMock(spec=GraphEntity)
        e2.canonical_name = "Artificial Inteligence" # One 'l'
        e2.id = uuid.uuid4()
        
        e3 = MagicMock(spec=GraphEntity)
        e3.canonical_name = "Python"
        e3.id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [e1, e2, e3]
        mock_db.execute.return_value = mock_result

        duplicates = await resolution_service.get_potential_duplicates(user_id, threshold=0.8)
        
        assert len(duplicates) >= 1
        assert duplicates[0]["score"] >= 0.8
        # Should match e1 and e2
        matched_names = {duplicates[0]["entity1"]["name"], duplicates[0]["entity2"]["name"]}
        assert "Artificial Intelligence" in matched_names
        assert "Artificial Inteligence" in matched_names
