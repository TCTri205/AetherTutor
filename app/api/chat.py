from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..repositories.chat_repo import ChatRepository
from ..repositories.graph_repo import GraphRepository
from ..core.retriever import Retriever
from ..services.chat_service import ChatService
from ..schemas.chat import ChatStreamRequest, ConversationRead, MessageRead, ConversationDetail, MessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# Dependency helpers
async def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    chat_repo = ChatRepository(db)
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)
    return ChatService(chat_repo, retriever)

@router.post("/conversations/{document_id}", response_model=ConversationRead)
async def create_conversation(
    document_id: uuid.UUID,
    title: str = Body("Cuộc hội thoại mới", embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Tạo một cuộc hội thoại mới cho tài liệu cụ thể."""
    chat_repo = ChatRepository(db)
    return await chat_repo.create_conversation(document_id, title)

@router.get("/conversations/{document_id}", response_model=List[ConversationRead])
async def list_conversations(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách các cuộc hội thoại liên quan đến tài liệu."""
    chat_repo = ChatRepository(db)
    return await chat_repo.list_conversations(document_id)

@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest,
    background_tasks: BackgroundTasks,
    service: ChatService = Depends(get_chat_service)
):
    """
    Endpoint chính cho trò chuyện streaming (SSE).
    Hỗ trợ chế độ Socratic và Feynman.
    """
    # 1. Khởi tạo/Lấy conversation_id
    conv_id = await service.get_or_create_conversation(request.document_id, request.conversation_id)

    # 2. Trả về stream SSE
    return StreamingResponse(
        service.chat_stream(
            conversation_id=conv_id,
            document_id=request.document_id,
            user_query=request.message,
            background_tasks=background_tasks,
            mode=request.mode
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/history/{conversation_id}", response_model=ConversationDetail)
async def get_chat_history(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Lấy toàn bộ lịch sử tin nhắn của một cuộc hội thoại."""
    chat_repo = ChatRepository(db)
    conv = await chat_repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await chat_repo.get_messages(conversation_id)
    # Convert to schema
    return ConversationDetail(
        id=conv.id,
        document_id=conv.document_id,
        title=conv.title,
        created_at=conv.created_at,
        last_message_at=conv.last_message_at,
        messages=[MessageRead.from_orm(m) for m in messages]
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Xóa cuộc hội thoại và toàn bộ tin nhắn liên quan."""
    chat_repo = ChatRepository(db)
    success = await chat_repo.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}

# --- Legacy Compatibility ---
@router.post("/socratic", response_model=MessageResponse)
async def socratic_chat_legacy(
    document_id: str,
    message: str = Body(..., embed=True),
    mode: str = "socratic",
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint cũ để giữ tương thích ngược. 
    Không hỗ trợ stream, trả về kết quả cuối cùng.
    """
    chat_repo = ChatRepository(db)
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)
    
    doc_uuid = uuid.UUID(document_id)
    context = await retriever.retrieve(message, document_id)
    context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])
    
    # Simple generation without complex state management for legacy
    prompt = f"Mode: {mode}\nContext: {context_str}\nUser: {message}"
    from ..services.llm_service import llm_service
    response = await llm_service.get_chat_completion([{"role": "user", "content": prompt}])
    
    return {
        "response": response.choices[0].message.content,
        "context_used": context
    }
