"""
Pydantic schemas for Note and NoteLink APIs (Zettelkasten).
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


# --- Note Schemas ---

class NoteBase(BaseModel):
    """Base schema for note."""
    title: str = Field(..., min_length=1, max_length=500, description="Tiêu đề note")
    content: str = Field(..., min_length=1, max_length=50000, description="Nội dung note (hỗ trợ Markdown)")
    note_type: str = Field(
        default="literature",
        description="Loại note: fleeting, literature, permanent, project"
    )
    tags: List[str] = Field(default_factory=list, description="Tags cho note")
    metadata: Optional[dict] = Field(default_factory=dict, description="Metadata bổ sung")


class NoteCreate(NoteBase):
    """Schema để tạo note mới."""
    pass


class NoteUpdate(BaseModel):
    """Schema để cập nhật note."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=50000)
    tags: Optional[List[str]] = None
    note_type: Optional[str] = None


class NoteLinkInfo(BaseModel):
    """Thông tin về link giữa 2 notes."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    source_note_id: uuid.UUID
    target_note_id: uuid.UUID
    context: Optional[str] = None
    link_type: str
    created_at: datetime


class NoteRead(NoteBase):
    """Schema trả về cho client."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class NoteDetail(NoteRead):
    """Schema chi tiết với backlinks."""
    outgoing_links: List[NoteLinkInfo] = []
    incoming_links: List[NoteLinkInfo] = []


class NoteListItem(BaseModel):
    """Schema cho danh sách notes."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    note_type: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    """Response cho list notes."""
    notes: List[NoteListItem]
    total: int


# --- NoteLink Schemas ---

class NoteLinkCreate(BaseModel):
    """Schema để tạo link giữa 2 notes."""
    target_note_id: uuid.UUID = Field(..., description="Note đích để link tới")
    context: Optional[str] = Field(None, max_length=1000, description="Context giải thích tại sao link")


class NoteLinkResponse(BaseModel):
    """Schema trả về cho note link."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_note_id: uuid.UUID
    target_note_id: uuid.UUID
    context: Optional[str] = None
    link_type: str
    created_at: datetime


# --- Backlink Suggestion Schemas ---

class RelatedEntitySuggestion(BaseModel):
    """Gợi ý liên kết tới graph entity."""
    entity_name: str
    relation_type: str
    confidence: float
    context: str


class RelatedNoteSuggestion(BaseModel):
    """Gợi ý liên kết tới note khác."""
    note_id: uuid.UUID
    note_title: str
    relation_type: str
    confidence: float
    context: str


class BacklinkSuggestionsResponse(BaseModel):
    """Response chứa gợi ý backlinks."""
    related_entities: List[RelatedEntitySuggestion] = []
    related_notes: List[RelatedNoteSuggestion] = []


# --- Note Graph Schema ---

class NoteGraphNode(BaseModel):
    """Node trong note graph."""
    id: uuid.UUID
    title: str
    note_type: str
    tags: List[str]
    created_at: str


class NoteGraphEdge(BaseModel):
    """Edge trong note graph."""
    source: uuid.UUID
    target: uuid.UUID
    link_type: str
    context: Optional[str] = None


class NoteGraphResponse(BaseModel):
    """Response cho note graph (React Flow visualization)."""
    nodes: List[NoteGraphNode]
    edges: List[NoteGraphEdge]
