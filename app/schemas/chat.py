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
