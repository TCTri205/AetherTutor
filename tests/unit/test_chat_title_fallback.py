import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_generate_conversation_title_fallback():
    """Test that fallback title is used after all retries fail."""
    conv_id = uuid.uuid4()
    first_query = "This is a query for testing fallback."
    expected_title = "This is a query for testing fallback."  # 6 words, no "..."

    # Track what values were passed to update
    updated_values = {}

    # Create mock LLM that always fails
    mock_llm = MagicMock()
    mock_llm.get_chat_completion = AsyncMock(side_effect=Exception("Mock LLM 500"))

    # Create mock session with proper async context manager behavior
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    # Mock execute to capture update values
    async def mock_execute(stmt, *args, **kwargs):
        nonlocal updated_values
        # SQLAlchemy update statement stores values in _values
        if hasattr(stmt, '_values'):
            for key, value in stmt._values.items():
                # Key might be Column object or string
                key_name = key.name if hasattr(key, 'name') else str(key)
                updated_values[key_name] = value
        return MagicMock()
    
    mock_session.execute = mock_execute

    # Create a proper async context manager
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    # Patch at the database module level
    with patch("app.services.chat_service.llm_service", mock_llm):
        with patch("app.database.AsyncSessionLocal", return_value=mock_cm):
            with patch("asyncio.sleep", return_value=None):
                # Import and call
                from app.services.chat_service import ChatService
                mock_repo = MagicMock()
                mock_repo.session = AsyncMock()
                mock_retriever = AsyncMock()
                service = ChatService(mock_repo, mock_retriever)

                await service.generate_conversation_title(conv_id, first_query, max_retries=1)

    # Verify fallback title was set
    title_param = updated_values.get('title')
    
    # Extract actual value from BindParameter if needed
    if hasattr(title_param, 'value'):
        actual_title = title_param.value
    elif hasattr(title_param, 'desc'):
        actual_title = title_param.desc
    else:
        actual_title = str(title_param)
    
    assert actual_title == expected_title, (
        f"Expected title '{expected_title}', got '{actual_title}'. "
        f"Captured values: {updated_values}"
    )
    mock_session.commit.assert_awaited()
