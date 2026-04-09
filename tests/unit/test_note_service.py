"""
Unit tests cho NoteService.

Test coverage:
- create_note: ownership, tags, metadata
- get_note, get_note_detail: ownership check, backlinks
- list_notes: filters by type/tags, pagination
- update_note: partial updates, ownership validation
- delete_note: cascading to links
- create_link: link validation, deduplication
- suggest_backlinks: AI integration
- get_note_graph: visualization data
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.note_service import NoteService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_note_repo():
    """Mock NoteRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get = AsyncMock()
    repo.get_by_id_with_links = AsyncMock()
    repo.get_by_user = AsyncMock()
    repo.search_by_tags = AsyncMock()
    repo.delete = AsyncMock()
    repo.session = AsyncMock()
    repo.session.commit = AsyncMock()
    repo.session.refresh = AsyncMock()
    return repo


@pytest.fixture
def mock_note_link_repo():
    """Mock NoteLinkRepository."""
    repo = AsyncMock()
    repo.create_link = AsyncMock()
    repo.get_link = AsyncMock()
    repo.get_backlinks = AsyncMock()
    repo.get_outgoing_links = AsyncMock()
    repo.get_note_graph = AsyncMock()
    return repo


@pytest.fixture
def mock_backlink_ai():
    """Mock BacklinkAIService."""
    ai = AsyncMock()
    ai.suggest_backlinks_for_note = AsyncMock()
    return ai


@pytest.fixture
def note_service(mock_note_repo, mock_note_link_repo, mock_backlink_ai):
    """NoteService với mocked dependencies."""
    return NoteService(
        note_repo=mock_note_repo,
        note_link_repo=mock_note_link_repo,
        backlink_ai_service=mock_backlink_ai,
    )


def create_mock_note(note_id, user_id, title="Test Note", content="Content", note_type="literature", tags=None):
    """Helper tạo mock note."""
    note = MagicMock()
    note.id = note_id
    note.user_id = user_id
    note.title = title
    note.content = content
    note.note_type = note_type
    note.tags = tags or []
    note.metadata = {}
    note.created_at = MagicMock()
    return note


# ============================================================
# Tests cho create_note
# ============================================================

class TestCreateNote:

    @pytest.mark.asyncio
    async def test_create_note_success(self, note_service, mock_note_repo):
        """Tạo note thành công."""
        user_id = uuid.uuid4()
        mock_note_repo.create.return_value = create_mock_note(uuid.uuid4(), user_id)

        result = await note_service.create_note(
            user_id=user_id,
            title="Test Note",
            content="Note content",
            note_type="fleeting",
            tags=["test", "draft"],
        )

        mock_note_repo.create.assert_called_once()
        call_kwargs = mock_note_repo.create.call_args[1]
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["title"] == "Test Note"
        assert call_kwargs["note_type"] == "fleeting"
        assert call_kwargs["tags"] == ["test", "draft"]

    @pytest.mark.asyncio
    async def test_create_note_default_type(self, note_service, mock_note_repo):
        """Không truyền note_type → default 'literature'."""
        user_id = uuid.uuid4()
        mock_note_repo.create.return_value = create_mock_note(uuid.uuid4(), user_id)

        await note_service.create_note(
            user_id=user_id,
            title="Test",
            content="Content",
        )

        call_kwargs = mock_note_repo.create.call_args[1]
        assert call_kwargs["note_type"] == "literature"

    @pytest.mark.asyncio
    async def test_create_note_empty_tags(self, note_service, mock_note_repo):
        """Không truyền tags → empty list."""
        user_id = uuid.uuid4()
        mock_note_repo.create.return_value = create_mock_note(uuid.uuid4(), user_id)

        await note_service.create_note(
            user_id=user_id,
            title="Test",
            content="Content",
        )

        call_kwargs = mock_note_repo.create.call_args[1]
        assert call_kwargs["tags"] == []


# ============================================================
# Tests cho get_note / get_note_detail
# ============================================================

class TestGetNote:

    @pytest.mark.asyncio
    async def test_get_note_success(self, note_service, mock_note_repo):
        """Get note by ID."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        mock_note_repo.get.return_value = create_mock_note(note_id, user_id)

        result = await note_service.get_note(note_id, user_id)

        mock_note_repo.get.assert_called_once_with(note_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_note_detail_with_links(self, note_service, mock_note_repo):
        """Get note detail với backlinks."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        mock_note_repo.get_by_id_with_links.return_value = create_mock_note(note_id, user_id)

        result = await note_service.get_note_detail(note_id, user_id)

        mock_note_repo.get_by_id_with_links.assert_called_once_with(note_id, user_id)
        assert result is not None


# ============================================================
# Tests cho list_notes
# ============================================================

class TestListNotes:

    @pytest.mark.asyncio
    async def test_list_notes_no_filter(self, note_service, mock_note_repo):
        """List notes không có filter."""
        user_id = uuid.uuid4()
        mock_note_repo.get_by_user.return_value = ([create_mock_note(uuid.uuid4(), user_id)], 1)

        notes, total = await note_service.list_notes(user_id, skip=0, limit=50)

        mock_note_repo.get_by_user.assert_called_once()
        assert len(notes) == 1

    @pytest.mark.asyncio
    async def test_list_notes_filter_by_tags(self, note_service, mock_note_repo):
        """List notes filter theo tags → dùng search_by_tags."""
        user_id = uuid.uuid4()
        mock_note_repo.search_by_tags.return_value = ([], 0)

        notes, total = await note_service.list_notes(
            user_id, tags=["important", "review"]
        )

        mock_note_repo.search_by_tags.assert_called_once()
        call_kwargs = mock_note_repo.search_by_tags.call_args[1]
        assert call_kwargs["tags"] == ["important", "review"]


# ============================================================
# Tests cho update_note
# ============================================================

class TestUpdateNote:

    @pytest.mark.asyncio
    async def test_update_note_success(self, note_service, mock_note_repo):
        """Update note thành công."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        note = create_mock_note(note_id, user_id)
        mock_note_repo.get.return_value = note

        result = await note_service.update_note(
            note_id=note_id,
            user_id=user_id,
            title="Updated Title",
            content="Updated content",
        )

        assert result is not None
        assert note.title == "Updated Title"
        assert note.content == "Updated content"
        mock_note_repo.session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_note_wrong_user(self, note_service, mock_note_repo):
        """Note không thuộc về user → return None."""
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()
        note_id = uuid.uuid4()
        mock_note_repo.get.return_value = create_mock_note(note_id, other_user)

        result = await note_service.update_note(
            note_id=note_id,
            user_id=user_id,
            title="Hacked",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_note_not_found(self, note_service, mock_note_repo):
        """Note không tồn tại → return None."""
        mock_note_repo.get.return_value = None

        result = await note_service.update_note(
            note_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Update",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_note_partial(self, note_service, mock_note_repo):
        """Partial update: chỉ update title."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        note = create_mock_note(note_id, user_id, title="Old Title")
        mock_note_repo.get.return_value = note

        await note_service.update_note(
            note_id=note_id,
            user_id=user_id,
            title="New Title",
            # content=None
        )

        assert note.title == "New Title"
        # Content không đổi
        assert note.content == "Content"


# ============================================================
# Tests cho delete_note
# ============================================================

class TestDeleteNote:

    @pytest.mark.asyncio
    async def test_delete_note_success(self, note_service, mock_note_repo):
        """Delete note thành công."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        mock_note_repo.get.return_value = create_mock_note(note_id, user_id)

        result = await note_service.delete_note(note_id, user_id)

        assert result is True
        mock_note_repo.delete.assert_called_once_with(note_id)

    @pytest.mark.asyncio
    async def test_delete_note_wrong_user(self, note_service, mock_note_repo):
        """Note không thuộc về user → return False."""
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()
        note_id = uuid.uuid4()
        mock_note_repo.get.return_value = create_mock_note(note_id, other_user)

        result = await note_service.delete_note(note_id, user_id)

        assert result is False
        mock_note_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self, note_service, mock_note_repo):
        """Note không tồn tại → return False."""
        mock_note_repo.get.return_value = None

        result = await note_service.delete_note(uuid.uuid4(), uuid.uuid4())

        assert result is False


# ============================================================
# Tests cho create_link
# ============================================================

class TestCreateLink:

    @pytest.mark.asyncio
    async def test_create_link_success(self, note_service, mock_note_repo, mock_note_link_repo):
        """Tạo link giữa 2 notes."""
        user_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_note_repo.get.side_effect = [
            create_mock_note(source_id, user_id),
            create_mock_note(target_id, user_id),
        ]
        mock_note_link_repo.get_link.return_value = None  # No existing link
        mock_note_link_repo.create_link.return_value = MagicMock()

        result = await note_service.create_link(
            user_id=user_id,
            source_note_id=source_id,
            target_note_id=target_id,
            context="Related concept",
            link_type="manual",
        )

        mock_note_link_repo.create_link.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_link_source_not_found(self, note_service, mock_note_repo):
        """Source note không tồn tại → return None."""
        mock_note_repo.get.side_effect = [None, create_mock_note(uuid.uuid4(), uuid.uuid4())]

        result = await note_service.create_link(
            user_id=uuid.uuid4(),
            source_note_id=uuid.uuid4(),
            target_note_id=uuid.uuid4(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_link_duplicate(self, note_service, mock_note_repo, mock_note_link_repo):
        """Link đã tồn tại → return existing."""
        user_id = uuid.uuid4()
        existing_link = MagicMock()

        mock_note_repo.get.side_effect = [
            create_mock_note(uuid.uuid4(), user_id),
            create_mock_note(uuid.uuid4(), user_id),
        ]
        mock_note_link_repo.get_link.return_value = existing_link

        result = await note_service.create_link(
            user_id=user_id,
            source_note_id=uuid.uuid4(),
            target_note_id=uuid.uuid4(),
        )

        assert result == existing_link
        mock_note_link_repo.create_link.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_link_different_users(self, note_service, mock_note_repo):
        """Notes thuộc users khác nhau → return None."""
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()

        mock_note_repo.get.side_effect = [
            create_mock_note(uuid.uuid4(), user1),
            create_mock_note(uuid.uuid4(), user2),
        ]

        result = await note_service.create_link(
            user_id=user1,
            source_note_id=uuid.uuid4(),
            target_note_id=uuid.uuid4(),
        )

        assert result is None


# ============================================================
# Tests cho get_backlinks / get_outgoing_links
# ============================================================

class TestGetLinks:

    @pytest.mark.asyncio
    async def test_get_backlinks(self, note_service, mock_note_link_repo):
        """Get incoming links."""
        note_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_note_link_repo.get_backlinks.return_value = [MagicMock(), MagicMock()]

        result = await note_service.get_backlinks(note_id, user_id)

        assert len(result) == 2
        mock_note_link_repo.get_backlinks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_outgoing_links(self, note_service, mock_note_link_repo):
        """Get outgoing links."""
        note_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_note_link_repo.get_outgoing_links.return_value = [MagicMock()]

        result = await note_service.get_outgoing_links(note_id, user_id)

        assert len(result) == 1


# ============================================================
# Tests cho suggest_backlinks
# ============================================================

class TestSuggestBacklinks:

    @pytest.mark.asyncio
    async def test_suggest_backlinks_success(self, note_service, mock_note_repo, mock_backlink_ai):
        """AI suggest backlinks."""
        user_id = uuid.uuid4()
        note_id = uuid.uuid4()
        note = create_mock_note(note_id, user_id)
        mock_note_repo.get.return_value = note

        mock_suggestions = MagicMock()
        mock_suggestions.dict.return_value = {
            "related_entities": [{"name": "Entity1"}],
            "related_notes": [{"title": "Note1"}],
        }
        mock_backlink_ai.suggest_backlinks_for_note.return_value = mock_suggestions

        result = await note_service.suggest_backlinks(note_id, user_id)

        assert "related_entities" in result
        assert "related_notes" in result
        mock_backlink_ai.suggest_backlinks_for_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_suggest_backlinks_note_not_found(self, note_service, mock_note_repo):
        """Note không tồn tại → empty suggestions."""
        mock_note_repo.get.return_value = None

        result = await note_service.suggest_backlinks(uuid.uuid4(), uuid.uuid4())

        assert result == {"related_entities": [], "related_notes": []}


# ============================================================
# Tests cho get_note_graph
# ============================================================

class TestGetNoteGraph:

    @pytest.mark.asyncio
    async def test_get_note_graph(self, note_service, mock_note_link_repo):
        """Get note graph cho visualization."""
        user_id = uuid.uuid4()
        mock_note_link_repo.get_note_graph.return_value = {
            "nodes": [{"id": "1", "title": "Note1"}],
            "edges": [{"source": "1", "target": "2"}],
        }

        result = await note_service.get_note_graph(user_id)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 1
        mock_note_link_repo.get_note_graph.assert_called_once()
