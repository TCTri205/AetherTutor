import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.retriever import Retriever

@pytest.fixture
def mock_graph_repo():
    return AsyncMock()

@pytest.fixture
def retriever(mock_graph_repo):
    return Retriever(mock_graph_repo)

@pytest.mark.asyncio
async def test_retrieve_basic(retriever, mock_graph_repo):
    doc_id = str(uuid.uuid4())
    query = "test query"
    
    # Mock ChromaDB
    mock_chunks_res = {
        'ids': [['c1']],
        'documents': [['chunk content']],
        'metadatas': [[{'document_id': doc_id, 'chunk_index': 0}]]
    }
    mock_entities_res = {
        'metadatas': [[{'entity_name': 'Einstein'}]]
    }
    
    with patch("app.core.retriever.chroma_client") as mock_chroma:
        mock_chroma.chunks_collection.query.return_value = mock_chunks_res
        mock_chroma.entities_collection.query.return_value = mock_entities_res
        
        # Mock Graph neighbors
        mock_rel = MagicMock()
        mock_rel.source_entity = "Einstein"
        mock_rel.target_entity = "Relativity"
        mock_rel.relation_type = "DISCOVERED"
        mock_rel.description = "Einstein discovered relativity."
        mock_graph_repo.get_entity_neighbors.return_value = [mock_rel]
        
        context, entity_names = await retriever.retrieve(query, doc_id)
        
        assert len(context) >= 2
        assert any(c['type'] == 'chunk' for c in context)
        assert any(c['type'] == 'relation' for c in context)
        assert "Einstein" in entity_names
        mock_graph_repo.get_entity_neighbors.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response(retriever):
    query = "Who is he?"
    context = [{"type": "chunk", "content": "Einstein is a physicist."}]
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Einstein is a physicist."
    
    with patch("app.core.retriever.llm_service") as mock_llm:
        mock_llm.get_chat_completion = AsyncMock(return_value=mock_response)
        
        answer = await retriever.generate(query, context)
        
        assert answer == "Einstein is a physicist."
        mock_llm.get_chat_completion.assert_called_once()
        # Verify prompt construction contains context
        args, _ = mock_llm.get_chat_completion.call_args
        prompt_content = args[0][0]['content']
        assert "Einstein is a physicist." in prompt_content

@pytest.mark.asyncio
async def test_retrieve_empty_results(retriever, mock_graph_repo):
    doc_id = str(uuid.uuid4())
    
    mock_chunks_res = {'ids': [[]], 'documents': [[]], 'metadatas': [[]]}
    mock_entities_res = {'metadatas': [[]]}
    
    with patch("app.core.retriever.chroma_client") as mock_chroma:
        mock_chroma.chunks_collection.query.return_value = mock_chunks_res
        mock_chroma.entities_collection.query.return_value = mock_entities_res
        
        context, entity_names = await retriever.retrieve("nothing", doc_id)
        
        assert len(context) == 0
        assert len(entity_names) == 0
        mock_graph_repo.get_entity_neighbors.assert_not_called()
