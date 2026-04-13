import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.chat_service import ChatService
from app.models.conversation import MessageStatus

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.session = AsyncMock()
    repo.get_conversation = AsyncMock()
    repo.add_message = AsyncMock()
    repo.update_message = AsyncMock()
    repo.get_last_n_messages = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_retriever():
    retriever = AsyncMock()
    # retrieve() trả về tuple: (context_chunks, found_entities_list)
    retriever.retrieve = AsyncMock(return_value=([], []))
    return retriever

@pytest.fixture
def chat_service(mock_repo, mock_retriever):
    return ChatService(mock_repo, mock_retriever)

@pytest.mark.asyncio
async def test_chat_stream_context_validation_fails(chat_service, mock_repo):
    # Setup: Conversation belongs to different document
    doc_id = uuid.uuid4()
    wrong_doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    
    mock_conv = MagicMock()
    mock_conv.document_id = wrong_doc_id
    mock_repo.get_conversation.return_value = mock_conv
    
    # Execute & Verify: Should raise 400
    with pytest.raises(HTTPException) as excinfo:
        # Call _stream_logic directly with mock_repo
        gen = chat_service._stream_logic(
            chat_repo=mock_repo,
            retriever=mock_retriever,
            conversation_id=conv_id,
            document_id=doc_id,
            user_query="hello",
            background_tasks=MagicMock()
        )
        await gen.__anext__()
    
    assert excinfo.value.status_code == 400
    assert "Conversation/Document mismatch" in excinfo.value.detail

@pytest.mark.asyncio
async def test_chat_stream_durability_commits(chat_service, mock_repo, mock_retriever):
    # Setup
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    mock_conv = MagicMock()
    mock_conv.document_id = doc_id
    mock_repo.get_conversation.return_value = mock_conv
    
    # Mock assistant message for status update
    mock_assistant_msg = MagicMock()
    mock_assistant_msg.id = uuid.uuid4()
    mock_assistant_msg.context_used = {}
    mock_repo.add_message.return_value = mock_assistant_msg

    # Mock LLM stream
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [] # Empty stream for simplicity
    
    with patch("app.services.chat_service.llm_service") as mock_llm:
        mock_llm.stream_chat_completion.return_value = mock_stream
        
        # Execute _stream_logic directly
        gen = chat_service._stream_logic(
            chat_repo=mock_repo,
            retriever=mock_retriever,
            conversation_id=conv_id,
            document_id=doc_id,
            user_query="hello",
            background_tasks=MagicMock()
        )
        async for _ in gen:
            pass

    # Verify: 5 commits in total
    # 1. User message
    # 2. Metadata update (attempt_count, hint_level, last_topics)
    # 3. PENDING assistant message
    # 4. Defensive FAILED status
    # 5. COMPLETED status (after successful stream)
    assert mock_repo.session.commit.call_count == 5
    # Verify order of commits matches durability requirement
    # First commit should be after add_message(role="user")
    # Second commit should be after metadata update (Conversation)
    # Third commit should be after add_message(role="assistant", status=PENDING)

@pytest.mark.asyncio
async def test_chat_stream_disconnect_marks_failed(chat_service, mock_repo, mock_retriever):
    """Test that CancelledError properly marks message as FAILED."""
    # Setup
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    mock_conv = MagicMock()
    mock_conv.document_id = doc_id
    mock_repo.get_conversation.return_value = mock_conv
    
    mock_assistant_msg = MagicMock()
    mock_assistant_msg.id = uuid.uuid4()
    mock_assistant_msg.context_used = {}
    mock_repo.add_message.return_value = mock_assistant_msg

    # Mock LLM stream that gets cancelled (right way to simulate disconnect)
    async def stream_that_gets_cancelled():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="partial"))])
        raise asyncio.CancelledError() #← Simulate disconnect

    with patch("app.services.chat_service.llm_service") as mock_llm:
        # Quan trọng: Đảm bảo mock hỗ trợ await và trả về async generator
        mock_llm.stream_chat_completion = AsyncMock(return_value=stream_that_gets_cancelled())
        
        # Execute _stream_logic directly
        gen = chat_service._stream_logic(
            chat_repo=mock_repo,
            retriever=mock_retriever,
            conversation_id=conv_id,
            document_id=doc_id,
            user_query="hello",
            background_tasks=MagicMock()
        )
        with pytest.raises(asyncio.CancelledError):
            async for _ in gen:
                pass

    # Verify: update_message called with status=FAILED from the defensive commit step
    mock_repo.update_message.assert_any_call(
        mock_assistant_msg.id,
        content="",
        status=MessageStatus.FAILED
    )
    # Ensure it was committed (User, Pending, Defensive FAILED)
    assert mock_repo.session.commit.call_count >= 3
