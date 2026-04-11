import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from app.services.obsidian_vault_importer import ObsidianVaultImporter
from app.core.markdown_parser import ParsedNote

@pytest.fixture
async def auth_headers():
    """Tạo headers với user_id mặc định."""
    return {"X-User-ID": "00000000-0000-0000-0000-000000000001"}

@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Lấy hoặc tạo user mẫu."""
    from app.models.user import User
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user = await test_db.get(User, user_id)
    if not user:
        user = User(id=user_id, email="test@example.com", hashed_password="hashed", is_active=True)
        test_db.add(user)
        await test_db.flush()
    return user

@pytest.mark.asyncio
async def test_import_obsidian_vault_api(async_client: AsyncClient, auth_headers):
    """Test API endpoint for starting Obsidian import"""
    payload = {
        "vault_path": "/mock/vault/path"
    }
    # Mock redis pool to avoid side effects
    with patch("app.api.graph.get_redis_pool", new_callable=AsyncMock) as mock_redis:
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock()
        mock_redis.return_value = mock_pool

        response = await async_client.post(
            "/api/v1/graph/import/obsidian",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

@pytest.mark.asyncio
async def test_obsidian_importer_logic(test_db: AsyncSession, test_user):
    """Test the core logic of ObsidianVaultImporter with mocked parser"""
    from app.models.graph import GraphEntity, GraphRelation
    from unittest.mock import AsyncMock

    importer = ObsidianVaultImporter(test_db)

    # Cần tạo document cho user trước khi import entities
    from app.models.document import Document, DocumentStatus, ProcessingStep
    doc = Document(
        id=uuid.uuid4(),
        user_id=test_user.id,
        filename="Obsidian Vault",
        file_path="/mock",
        content_hash="obsidian_mock",
        status=DocumentStatus.COMPLETED,
        processing_step=ProcessingStep.COMPLETED
    )
    test_db.add(doc)
    await test_db.flush()

    mock_notes = [
        ParsedNote(
            title="Note A",
            filename="Note A",
            content="Content A with [[Note B]]",
            links=["Note B"],
            tags=["tag1"],
            frontmatter={"author": "User"},
            file_path="/mock/Note A.md"
        ),
        ParsedNote(
            title="Note B",
            filename="Note B",
            content="Content B",
            links=[],
            tags=["tag2"],
            frontmatter={},
            file_path="/mock/Note B.md"
        )
    ]

    # Tạo mock entities
    mock_entity_a = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Note A",
        entity_type="note",
        description="Content A",
        confidence=1.0,
        source="obsidian_import",
        tags=["tag1"],
        user_id=test_user.id
    )
    mock_entity_b = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Note B",
        entity_type="note",
        description="Content B",
        confidence=1.0,
        source="obsidian_import",
        tags=["tag2"],
        user_id=test_user.id
    )
    mock_rel = GraphRelation(
        id=uuid.uuid4(),
        source_entity_id=mock_entity_a.id,
        target_entity_id=mock_entity_b.id,
        relation_type="links_to",
        description="Link",
        source="obsidian_import"
    )

    mock_repo = AsyncMock()
    mock_repo.upsert_entity = AsyncMock(side_effect=lambda *args, **kwargs: 
        mock_entity_a if (kwargs.get("entity_data") or args[2])["canonical_name"] == "Note A" 
        else mock_entity_b
    )
    mock_repo.bulk_upsert_relations = AsyncMock(return_value=[mock_rel])
    
    # Mock resolution service để trả về entity từ repo
    mock_resolution = AsyncMock()
    mock_resolution.resolve_and_merge = AsyncMock(side_effect=lambda *args, **kwargs: 
        mock_entity_a if kwargs.get("entity_data", args[1])["canonical_name"] == "Note A"
        else mock_entity_b
    )
    mock_resolution.llm_verify_merge = AsyncMock(return_value=False)

    # Mock the parser, file scanning, path existance, LLM service, and repository
    with patch("os.walk") as mock_walk, \
         patch("app.core.markdown_parser.MarkdownParser.parse_file") as mock_parse, \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:

        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_walk.return_value = [("/mock", [], ["Note A.md", "Note B.md"])]
        mock_parse.side_effect = mock_notes

        # Override repo và resolution service
        importer.repo = mock_repo
        importer.resolution_service = mock_resolution

        result = await importer.import_vault("/mock", test_user.id)

        assert result["entities_imported"] == 2
        assert result["relations_imported"] == 1

@pytest.mark.asyncio
async def test_import_obsidian_vault_empty_directory(async_client: AsyncClient, auth_headers, test_db: AsyncSession, test_user):
    """Test import when vault directory has no markdown files"""
    importer = ObsidianVaultImporter(test_db)
    
    with patch("os.walk") as mock_walk, \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:
        
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_walk.return_value = [("/mock", [], [])]  # No files
        
        result = await importer.import_vault("/mock", test_user.id)
        
        assert result["entities_imported"] == 0
        assert result["relations_imported"] == 0
        assert "No markdown files found" in result["message"]

@pytest.mark.asyncio
async def test_import_obsidian_vault_invalid_path(async_client: AsyncClient, auth_headers, test_db: AsyncSession, test_user):
    """Test import with invalid vault path"""
    importer = ObsidianVaultImporter(test_db)
    
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        
        with pytest.raises(ValueError, match="Vault path does not exist"):
            await importer.import_vault("/invalid/path", test_user.id)

@pytest.mark.asyncio
async def test_import_obsidian_vault_with_wiki_links(test_db: AsyncSession, test_user):
    """Test import with various wiki-link patterns"""
    from app.models.graph import GraphEntity, GraphRelation

    importer = ObsidianVaultImporter(test_db)

    mock_notes = [
        ParsedNote(
            title="Machine Learning",
            filename="ML",
            content="Introduction to [[Deep Learning]] and [[Neural Networks]]",
            links=["Deep Learning", "Neural Networks"],
            tags=["ai", "machine-learning"],
            frontmatter={},
            file_path="/mock/ML.md"
        ),
        ParsedNote(
            title="Deep Learning",
            filename="DL",
            content="Subset of [[Machine Learning]]",
            links=["Machine Learning"],
            tags=["ai", "deep-learning"],
            frontmatter={},
            file_path="/mock/DL.md"
        ),
        ParsedNote(
            title="Neural Networks",
            filename="NN",
            content="Foundation of [[Deep Learning]]",
            links=["Deep Learning"],
            tags=["ai", "neural-networks"],
            frontmatter={},
            file_path="/mock/NN.md"
        ),
    ]

    # Create mock entities
    mock_entity_ml = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Machine Learning",
        entity_type="note",
        description="Introduction to [[Deep Learning]] and [[Neural Networks]]",
        confidence=1.0,
        source="obsidian_import",
        tags=["ai", "machine-learning"],
        user_id=test_user.id
    )
    mock_entity_dl = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Deep Learning",
        entity_type="note",
        description="Subset of [[Machine Learning]]",
        confidence=1.0,
        source="obsidian_import",
        tags=["ai", "deep-learning"],
        user_id=test_user.id
    )
    mock_entity_nn = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Neural Networks",
        entity_type="note",
        description="Foundation of [[Deep Learning]]",
        confidence=1.0,
        source="obsidian_import",
        tags=["ai", "neural-networks"],
        user_id=test_user.id
    )
    mock_rel = GraphRelation(
        id=uuid.uuid4(),
        source_entity_id=mock_entity_ml.id,
        target_entity_id=mock_entity_dl.id,
        relation_type="links_to",
        description="Wiki-link",
        source="obsidian_import"
    )

    entity_map = {
        "Machine Learning": mock_entity_ml,
        "Deep Learning": mock_entity_dl,
        "Neural Networks": mock_entity_nn,
    }

    mock_repo = AsyncMock()
    mock_repo.upsert_entity = AsyncMock(side_effect=lambda *args, **kwargs:
        entity_map.get((kwargs.get("entity_data") or args[2])["canonical_name"], mock_entity_ml)
    )
    mock_repo.bulk_upsert_relations = AsyncMock(return_value=[mock_rel])

    # Mock resolution service để trả về entity từ entity_data
    mock_resolution = AsyncMock()
    mock_resolution.resolve_and_merge = AsyncMock(side_effect=lambda *args, **kwargs:
        entity_map.get((kwargs.get("entity_data") or args[1])["canonical_name"], mock_entity_ml)
    )
    mock_resolution.llm_verify_merge = AsyncMock(return_value=False)

    with patch("os.walk") as mock_walk, \
         patch("app.core.markdown_parser.MarkdownParser.parse_file") as mock_parse, \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:

        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_walk.return_value = [("/mock", [], ["ML.md", "DL.md", "NN.md"])]
        mock_parse.side_effect = mock_notes

        importer.repo = mock_repo
        importer.resolution_service = mock_resolution

        result = await importer.import_vault("/mock", test_user.id)

        assert result["entities_imported"] == 3
        assert result["relations_imported"] == 4

        # Verify resolve_and_merge was called with correct tags
        calls = mock_resolution.resolve_and_merge.call_args_list
        ml_call = next(c for c in calls if (c.kwargs.get("entity_data") or c.args[1])["canonical_name"] == "Machine Learning")
        ml_data = ml_call.kwargs.get("entity_data") or ml_call.args[1]
        assert "ai" in ml_data["tags"]
        assert "machine-learning" in ml_data["tags"]

@pytest.mark.asyncio
async def test_import_obsidian_vault_duplicate_handling(test_db: AsyncSession, test_user):
    """Test import handles duplicate entities correctly"""
    from app.models.graph import GraphEntity

    importer = ObsidianVaultImporter(test_db)

    # Simulate importing same note twice (should merge, not duplicate)
    mock_notes = [
        ParsedNote(
            title="AI",
            filename="AI1",
            content="Artificial Intelligence",
            links=[],
            tags=["ai"],
            frontmatter={},
            file_path="/mock/AI1.md"
        ),
        ParsedNote(
            title="AI",  # Same title, different file
            filename="AI2",
            content="AI is the future",
            links=[],
            tags=["technology"],
            frontmatter={},
            file_path="/mock/AI2.md"
        ),
    ]

    # Create mock entity - same entity returned for both notes with same title
    mock_entity_ai = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="AI",
        entity_type="note",
        description="Artificial Intelligence",
        confidence=1.0,
        source="obsidian_import",
        tags=["ai", "technology"],
        user_id=test_user.id
    )

    mock_repo = AsyncMock()
    mock_repo.upsert_entity = AsyncMock(return_value=mock_entity_ai)
    mock_repo.bulk_upsert_relations = AsyncMock(return_value=[])

    # Mock resolution service để trả về cùng entity cho cả 2 notes
    mock_resolution = AsyncMock()
    mock_resolution.resolve_and_merge = AsyncMock(return_value=mock_entity_ai)
    mock_resolution.llm_verify_merge = AsyncMock(return_value=False)

    with patch("os.walk") as mock_walk, \
         patch("app.core.markdown_parser.MarkdownParser.parse_file") as mock_parse, \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:

        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_walk.return_value = [("/mock", [], ["AI1.md", "AI2.md"])]
        mock_parse.side_effect = mock_notes

        importer.repo = mock_repo
        importer.resolution_service = mock_resolution

        result = await importer.import_vault("/mock", test_user.id)

        # Should have imported 2 notes but both resolve to same entity
        assert result["entities_imported"] == 2
        assert result["relations_imported"] == 0

        # Verify resolve_and_merge was called twice (once per note)
        assert mock_resolution.resolve_and_merge.call_count == 2

        # Verify tags from both notes were passed
        calls = mock_resolution.resolve_and_merge.call_args_list
        tags_list = [(c.kwargs.get("entity_data") or c.args[1])["tags"] for c in calls]
        assert ["ai"] in tags_list
        assert ["technology"] in tags_list

@pytest.mark.asyncio
async def test_import_obsidian_vault_api_status(async_client: AsyncClient, auth_headers):
    """Test API endpoint for checking import status"""
    job_id = str(uuid.uuid4())
    
    # Mock redis to return job status
    with patch("app.api.graph.get_redis_pool", new_callable=AsyncMock) as mock_redis:
        mock_pool = AsyncMock()
        mock_pool.get = AsyncMock(return_value=b"processing")
        mock_redis.return_value = mock_pool
        
        response = await async_client.get(
            f"/api/v1/graph/import/obsidian/status/{job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

@pytest.mark.asyncio
async def test_import_obsidian_vault_with_frontmatter(test_db: AsyncSession, test_user):
    """Test import preserves frontmatter metadata"""
    from app.models.graph import GraphEntity

    importer = ObsidianVaultImporter(test_db)

    mock_notes = [
        ParsedNote(
            title="Research Paper",
            filename="paper",
            content="This is a research paper about AI",
            links=[],
            tags=["research"],
            frontmatter={
                "author": "John Doe",
                "date": "2026-04-11",
                "type": "paper",
                "rating": 5
            },
            file_path="/mock/paper.md"
        ),
    ]

    # Create mock entity with metadata
    mock_entity = GraphEntity(
        id=uuid.uuid4(),
        canonical_name="Research Paper",
        entity_type="note",
        description="This is a research paper about AI",
        confidence=1.0,
        source="obsidian_import",
        tags=["research"],
        user_id=test_user.id
    )

    mock_repo = AsyncMock()
    mock_repo.upsert_entity = AsyncMock(return_value=mock_entity)
    mock_repo.bulk_upsert_relations = AsyncMock(return_value=[])

    mock_resolution = AsyncMock()
    mock_resolution.resolve_and_merge = AsyncMock(return_value=mock_entity)
    mock_resolution.llm_verify_merge = AsyncMock(return_value=False)

    with patch("os.walk") as mock_walk, \
         patch("app.core.markdown_parser.MarkdownParser.parse_file") as mock_parse, \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:

        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_walk.return_value = [("/mock", [], ["paper.md"])]
        mock_parse.side_effect = mock_notes

        importer.repo = mock_repo
        importer.resolution_service = mock_resolution

        result = await importer.import_vault("/mock", test_user.id)

        assert result["entities_imported"] == 1

        # Verify resolve_and_merge was called with frontmatter metadata
        call_args = mock_resolution.resolve_and_merge.call_args
        entity_data = call_args.kwargs.get("entity_data") or call_args.args[1]
        assert entity_data["metadata"]["author"] == "John Doe"
        assert entity_data["metadata"]["type"] == "paper"
        assert entity_data["metadata"]["rating"] == 5
