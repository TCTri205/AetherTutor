from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks, Query, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
import uuid
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..repositories.chat_repo import ChatRepository
from ..repositories.graph_repo import GraphRepository
from ..repositories.document_repo import DocumentRepository
from ..core.retriever import Retriever
from ..services.chat_service import ChatService
from ..services.cross_verification_service import cross_verification_service
from ..schemas.chat import ChatStreamRequest, ConversationRead, MessageRead, ConversationDetail, MessageResponse, MultiDocChatRequest, MultiDocChatResponse
from ..constants import RATE_LIMIT_CONVERSATION_CREATE, RATE_LIMIT_CHAT_STREAM
from .limiter import limiter
from .dependencies import get_optional_user_id, get_current_user_id

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

async def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    chat_repo = ChatRepository(db)
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)
    return ChatService(chat_repo, retriever)

@router.post("/conversations/{document_id}", response_model=ConversationRead)
@limiter.limit(RATE_LIMIT_CONVERSATION_CREATE)
async def create_conversation(
    request: Request,
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
@limiter.limit(RATE_LIMIT_CHAT_STREAM)
async def chat_stream(
    request: Request,
    stream_request: ChatStreamRequest,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint chính cho trò chuyện streaming (SSE).
    Hỗ trợ chế độ Socratic và Feynman.
    Conversation creation is handled inside the stream generator to ensure
    proper DB session lifecycle (no DI session conflicts).
    """
    # Import here to avoid circular imports
    from ..services.chat_service import ChatService
    from ..database import AsyncSessionLocal
    from ..repositories.chat_repo import ChatRepository
    from ..repositories.graph_repo import GraphRepository
    from ..core.retriever import Retriever

    async def stream_generator():
        async with AsyncSessionLocal() as stream_session:
            chat_repo = ChatRepository(stream_session)
            doc_repo = DocumentRepository(stream_session)

            # Get or create conversation within the stream session
            conv_id = stream_request.conversation_id
            if conv_id:
                conv = await chat_repo.get_conversation(conv_id)
                if not conv:
                    yield f"event: error\ndata: {json.dumps({'detail': 'Conversation not found', 'code': 'NOT_FOUND'})}\n\n"
                    return
                resolved_conv_id = conv.id
            else:
                # Validate document exists before creating conversation
                doc = await doc_repo.get_by_id(stream_request.document_id)
                if not doc:
                    yield f"event: error\ndata: {json.dumps({'detail': f'Document {stream_request.document_id} not found', 'code': 'DOCUMENT_NOT_FOUND'})}\n\n"
                    return

                new_conv = await chat_repo.create_conversation(stream_request.document_id)
                await stream_session.commit()
                resolved_conv_id = new_conv.id

            graph_repo = GraphRepository(stream_session)
            retriever = Retriever(graph_repo)

            # Extract and validate user_id from request header
            raw_user_id = request.headers.get("X-User-Id")
            user_id: str | None = None
            if raw_user_id:
                try:
                    uuid.UUID(raw_user_id)
                    user_id = raw_user_id
                except ValueError:
                    yield f"event: error\ndata: {json.dumps({'detail': 'Invalid X-User-Id header', 'code': 'INVALID_USER_ID'})}\n\n"
                    return

            # Create a minimal service-like context for streaming
            service = ChatService(chat_repo, retriever, user_id=user_id)

            async for chunk in service._stream_logic(
                chat_repo=chat_repo,
                retriever=retriever,
                conversation_id=resolved_conv_id,
                document_id=stream_request.document_id,
                user_query=stream_request.message,
                background_tasks=background_tasks,
                mode=stream_request.mode
            ):
                yield chunk

    return StreamingResponse(
        stream_generator(),
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
    user_id: Optional[str] = Depends(get_optional_user_id),
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
    context, _ = await retriever.retrieve(message, document_id, user_id=user_id)
    context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])

    from ..services.llm_service import llm_service
    prompt = f"Mode: {mode}\nContext: {context_str}\nUser: {message}"
    response = await llm_service.get_chat_completion([{"role": "user", "content": prompt}])

    return {
        "response": response.choices[0].message.content,
        "context_used": context
    }


# =============================================
# Sprint 4: Multi-Document Chat Endpoint
# =============================================

@router.post("/multi-doc", response_model=MultiDocChatResponse)
async def chat_multi_doc(
    request: MultiDocChatRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat across multiple documents with cross-verification.

    - **message**: User's question/message
    - **document_ids**: Optional list of doc UUIDs. If None, searches all user docs.
    - **conversation_id**: Optional existing conversation ID
    - **mode**: 'socratic' or 'feynman'
    - **enable_cross_verification**: Enable LLM contradiction detection

    Returns AI response with source attribution and contradiction analysis.
    """
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)

    # Convert document_ids to strings for retriever
    doc_ids = [str(d) for d in request.document_ids] if request.document_ids else None

    # Multi-document retrieval
    context, entity_names, cross_verification = await retriever.retrieve_multi(
        query=request.message,
        user_id=str(user_id),
        document_ids=doc_ids,
        scope="document" if doc_ids else "user_global",
    )

    # Build context string with source attribution
    context_parts = []
    for ctx in context:
        doc_id = ctx.get("metadata", {}).get("document_id", "unknown")
        doc_short_id = doc_id[:8] if doc_id != "unknown" else "unknown"
        context_parts.append(f"[From {doc_short_id}] {ctx['content']}")
    
    context_str = "\n\n".join(context_parts)

    # Build prompt based on mode
    mode_instruction = {
        "socratic": "Ask guiding questions to help the user discover the answer themselves.",
        "feynman": "Explain in simple terms as if teaching a beginner.",
    }.get(request.mode, "Answer the question based on the context.")

    prompt = f"""You are a tutor assistant. {mode_instruction}

Answer based ONLY on the provided context. If context doesn't contain the answer, say you don't know.

Context (with source document IDs):
{context_str}

User Question: {request.message}

Your Response:
"""

    # Get LLM response
    from ..services.llm_service import llm_service
    llm_response = await llm_service.get_chat_completion([
        {"role": "user", "content": prompt}
    ])
    response_content = llm_response.choices[0].message.content

    # Determine documents involved
    doc_ids_involved = list(set([
        ctx.get("metadata", {}).get("document_id", "unknown")
        for ctx in context
        if ctx.get("metadata", {}).get("document_id")
    ]))

    # Run cross-verification if enabled and multiple docs involved
    cross_ver_summary = None
    if request.enable_cross_verification and len(doc_ids_involved) >= 2:
        # Prepare document contexts
        doc_contexts = {}
        for ctx in context:
            doc_id = ctx.get("metadata", {}).get("document_id", "unknown")
            if doc_id not in doc_contexts:
                doc_contexts[doc_id] = {
                    "document_id": doc_id,
                    "document_title": f"Document {doc_id[:8]}",
                    "context": [],
                }
            doc_contexts[doc_id]["context"].append(ctx)

        # Run cross-verification
        try:
            cv_result = await cross_verification_service.cross_check(
                query=request.message,
                document_contexts=list(doc_contexts.values()),
            )
            cross_ver_summary = cv_result
        except Exception as e:
            # Don't fail if cross-verification fails
            logger.warning(f"Cross-verification failed: {e}", exc_info=True)

    return MultiDocChatResponse(
        response=response_content,
        context_used=context[:20],  # Limit context size
        documents_involved=doc_ids_involved,
        cross_verification=cross_ver_summary,
        mode=request.mode,
    )

