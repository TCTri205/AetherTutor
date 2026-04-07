"""
Unit tests for BaseRepository.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.document import Document


class TestBaseRepository:
    """Test BaseRepository generic CRUD operations."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def repo(self, mock_session):
        """Create base repository instance."""
        return BaseRepository(mock_session, Document)
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repo, mock_session):
        """Test getting a record by ID."""
        mock_result = MagicMock()
        mock_doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            content_hash="hash123"
        )
        mock_result.scalars().first.return_value = mock_doc
        mock_session.execute.return_value = mock_result
        
        result = await repo.get_by_id(mock_doc.id)
        
        assert result is not None
        assert result.filename == "test.pdf"
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_session):
        """Test getting a non-existent record."""
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repo.get_by_id(uuid.uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_success(self, repo, mock_session):
        """Test deleting an existing record."""
        # Mock get_by_id to return a document
        mock_doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            content_hash="hash123"
        )
        
        # Mock the session for get_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalars().first.return_value = mock_doc
        
        # Mock delete
        mock_session.execute.side_effect = [mock_get_result, MagicMock()]
        
        result = await repo.delete(mock_doc.id)
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_doc)
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_session):
        """Test deleting a non-existent record."""
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repo.delete(uuid.uuid4())
        
        assert result is False
        mock_session.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_count(self, repo, mock_session):
        """Test counting records."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute.return_value = mock_result
        
        count = await repo.count()
        
        assert count == 42
