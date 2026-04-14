"""
Topic schemas — Request/Response for topic management (v1.2).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TopicCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    color: str = Field("#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=10)


class TopicUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=10)
    sort_order: int | None = None


class TopicResponse(BaseModel):
    id: str
    user_id: str
    name: str
    slug: str
    description: str | None
    color: str
    icon: str | None
    is_archived: bool
    sort_order: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TopicListResponse(BaseModel):
    topics: list[TopicResponse]
    total: int


class TopicWithCountsResponse(TopicResponse):
    document_count: int = 0
    note_count: int = 0


class AddDocumentRequest(BaseModel):
    document_id: str
    is_primary: bool = False


class AddNoteRequest(BaseModel):
    note_id: str
