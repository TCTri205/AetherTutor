from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
import uuid
from datetime import datetime
from ..models.conversation import MessageStatus

class ChatStreamRequest(BaseModel):
    document_id: uuid.UUID
    message: str = Field(..., description="Nội dung tin nhắn từ người dùng")
    conversation_id: Optional[uuid.UUID] = Field(None, description="ID cuộc hội thoại hiện tại (nếu có)")
    mode: str = Field("socratic", description="Chế độ gia sư: 'socratic' hoặc 'feynman'")

class ConversationRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    title: str
    created_at: datetime
    last_message_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sequence_index: int
    status: MessageStatus
    context_used: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationDetail(ConversationRead):
    messages: List[MessageRead] = []

class MessageResponse(BaseModel):
    """Legacy response for backward compatibility"""
    response: str
    context_used: List[dict] = []


# =============================================
# Sprint 4: Multi-Document Chat Schemas
# =============================================

class MultiDocChatRequest(BaseModel):
    """Request for multi-document chat with cross-verification."""
    message: str = Field(..., description="User's message")
    document_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="List of document UUIDs to include in chat. If None, chats with all user docs."
    )
    conversation_id: Optional[uuid.UUID] = Field(
        None,
        description="Conversation ID (if continuing existing chat)"
    )
    mode: str = Field(
        default="socratic",
        description="Tutor mode: 'socratic' or 'feynman'"
    )
    enable_cross_verification: bool = Field(
        default=True,
        description="Enable cross-document contradiction detection"
    )


class MultiDocChatResponse(BaseModel):
    """Response for multi-document chat."""
    response: str = Field(..., description="AI response")
    context_used: List[dict] = Field(default_factory=list, description="Context snippets used")
    documents_involved: List[str] = Field(default_factory=list, description="Document IDs involved in response")
    cross_verification: Optional[dict] = Field(None, description="Cross-verification summary (if enabled)")
    mode: str = Field(..., description="Tutor mode used")
