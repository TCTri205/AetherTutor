import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.obsidian_vault_importer import ObsidianVaultImporter
from app.core.markdown_parser import MarkdownParser

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def importer(mock_db):
    return ObsidianVaultImporter(mock_db)

@pytest.mark.asyncio
class TestObsidianVaultImporter:

    async def test_parse_wiki_links(self):
        """Test MarkdownParser wiki-link extraction."""
        parser = MarkdownParser()
        content = """
Check this [[Note A]] and [[Note B|Alias B]].
Also an image ![[img.png]] which should be ignored.
        """
        note = parser.parse_content(content, title="Test Note")

        assert "Note A" in note.links
        assert "Note B" in note.links
        assert "img.png" not in note.links
        assert note.title == "Test Note"

    async def test_parse_tags(self):
        """Test MarkdownParser tag extraction."""
        parser = MarkdownParser()
        content = """
---
tags: [tag1, tag2]
---
# Content
Some #tag3 and #tag4/subtag.
        """
        note = parser.parse_content(content, title="Test Note")
        
        assert "tag1" in note.tags
        assert "tag3" in note.tags
        assert "tag4/subtag" in note.tags

    @patch("app.services.obsidian_vault_importer.os.walk")
    @patch("app.core.markdown_parser.Path.read_text")
    async def test_import_vault_flow(self, mock_read, mock_walk, importer, mock_db):
        """Test full vault import flow."""
        user_id = uuid.uuid4()
        vault_path = "." # Use existing path to pass is_dir() check
        
        # Mock os.walk
        mock_walk.return_value = [
            ("/mock/vault", ["subdir"], ["note1.md"]),
            ("/mock/vault/subdir", [], ["note2.md"]),
        ]
        
        # Mock file reading
        mock_read.side_effect = ["# Note 1\nLink to [[Note 2]]", "# Note 2\nNo links"]

        # Mock dependencies
        with patch.object(importer.resolution_service, 'resolve_and_merge', new_callable=AsyncMock) as mock_resolve, \
             patch.object(importer.graph_builder, 'add_entities_and_relations', new_callable=AsyncMock) as mock_builder_add, \
             patch.object(importer.graph_builder, 'persist_graph', new_callable=AsyncMock) as mock_builder_persist:
            
            # Setup mock resolve return
            e1 = MagicMock()
            e1.id = uuid.uuid4()
            e2 = MagicMock()
            e2.id = uuid.uuid4()
            mock_resolve.side_effect = [e1, e2]

            # Mock bulk_upsert_relations để tránh gọi DB thật
            with patch.object(importer.repo, 'bulk_upsert_relations', new_callable=AsyncMock) as mock_bulk_rel:
                mock_bulk_rel.return_value = [MagicMock()]

                result = await importer.import_vault(vault_path, user_id)

                assert result["entities_imported"] == 2
                assert result["relations_imported"] == 1
                mock_resolve.assert_called()
                mock_builder_add.assert_called_once()
                mock_builder_persist.assert_called_once_with("obsidian_global")
                mock_db.commit.assert_called_once()

    @patch("app.services.obsidian_vault_importer.Path.exists")
    async def test_import_invalid_path(self, mock_exists, importer):
        """Test error when vault path doesn't exist."""
        mock_exists.return_value = False
        with pytest.raises(ValueError) as exc:
            await importer.import_vault("/invalid/path", uuid.uuid4())
        assert "does not exist" in str(exc.value)
