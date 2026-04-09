import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat_service import ChatService

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.session = AsyncMock()
    return repo

@pytest.fixture
def mock_retriever():
    return AsyncMock()

@pytest.fixture
def chat_service(mock_repo, mock_retriever):
    return ChatService(mock_repo, mock_retriever)

@pytest.mark.asyncio
async def test_generate_conversation_title_fallback(chat_service):
    """Test that fallback title is used after all retries fail."""
    conv_id = uuid.uuid4()
    first_query = "This is a query for testing fallback."
    
    # Mock LLM service to fail
    with patch("app.services.chat_service.llm_service") as mock_llm:
        mock_llm.get_chat_completion.side_effect = Exception("Ollama 500")
        
        # Mock AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        
        # Patch where it is actually imported inside the function
        with patch("app.database.AsyncSessionLocal", return_value=mock_session):
            with patch("asyncio.sleep", return_value=None):
                await chat_service.generate_conversation_title(conv_id, first_query, max_retries=1)

    # Verify fallback title: First 7 words. 
    # "This is a query for testing fallback." -> 6 words, so no "..."
    expected_title = "This is a query for testing fallback."
    
    assert mock_session.execute.called
    args, _ = mock_session.execute.call_args
    params = args[0].compile().params
    assert params['title_1'] == expected_title
    assert mock_session.commit.called
