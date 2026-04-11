"""
Topics API endpoints — Topic CRUD with document/note assignment (v1.2).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_id
from app.schemas.topic import (
    TopicCreateRequest,
    TopicUpdateRequest,
    TopicResponse,
    TopicListResponse,
    TopicWithCountsResponse,
    AddDocumentRequest,
    AddNoteRequest,
)
from app.services.topic_service import TopicService
from app.core.exceptions import AppError

router = APIRouter(prefix="/topics", tags=["topics"])


def _topic_response(topic) -> TopicResponse:
    return TopicResponse(
        id=str(topic.id),
        user_id=str(topic.user_id),
        name=topic.name,
        slug=topic.slug,
        description=topic.description,
        color=topic.color,
        icon=topic.icon,
        is_archived=topic.is_archived,
        sort_order=topic.sort_order,
        created_at=str(topic.created_at),
        updated_at=str(topic.updated_at),
    )


@router.post(
    "",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new topic",
)
async def create_topic(
    request: Request,
    body: TopicCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a new topic for the current user."""
    service = TopicService(db)
    try:
        topic = await service.create_topic(
            user_id=user_id,
            name=body.name,
            description=body.description,
            color=body.color,
            icon=body.icon,
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TOPIC_CREATE_FAILED",
        )

    return _topic_response(topic)


@router.get(
    "",
    response_model=TopicListResponse,
    summary="List all topics for current user",
)
async def list_topics(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List all topics for the current user with pagination."""
    service = TopicService(db)
    topics = await service.list_topics(user_id, limit, offset)
    total = await service.topic_repo.count_by_user(user_id)

    return TopicListResponse(
        topics=[_topic_response(t) for t in topics],
        total=total,
    )


@router.get(
    "/{topic_id}",
    response_model=TopicResponse,
    summary="Get topic by ID",
)
async def get_topic(
    topic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get a specific topic by ID."""
    service = TopicService(db)
    topic = await service.get_topic(uuid.UUID(topic_id), user_id)
    if not topic:
        raise AppError(
            message="Topic not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_NOT_FOUND",
        )
    return _topic_response(topic)


@router.put(
    "/{topic_id}",
    response_model=TopicResponse,
    summary="Update topic",
)
async def update_topic(
    topic_id: str,
    request: Request,
    body: TopicUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update a topic's fields."""
    service = TopicService(db)
    try:
        topic = await service.update_topic(
            uuid.UUID(topic_id), user_id, **body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TOPIC_UPDATE_FAILED",
        )

    if not topic:
        raise AppError(
            message="Topic not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_NOT_FOUND",
        )

    return _topic_response(topic)


@router.post(
    "/{topic_id}/archive",
    response_model=TopicResponse,
    summary="Archive topic",
)
async def archive_topic(
    topic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Archive a topic (soft delete)."""
    service = TopicService(db)
    topic = await service.archive_topic(uuid.UUID(topic_id), user_id)
    if not topic:
        raise AppError(
            message="Topic not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_NOT_FOUND",
        )
    return _topic_response(topic)


@router.delete(
    "/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete topic",
)
async def delete_topic(
    topic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a topic. Junction rows cascade, documents/notes remain."""
    service = TopicService(db)
    success = await service.delete_topic(uuid.UUID(topic_id), user_id)
    if not success:
        raise AppError(
            message="Topic not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_NOT_FOUND",
        )
    return None


# --- Document/Note Assignment ---

@router.post(
    "/{topic_id}/documents",
    status_code=status.HTTP_201_CREATED,
    summary="Add document to topic",
)
async def add_document(
    topic_id: str,
    body: AddDocumentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Add a document to this topic."""
    service = TopicService(db)
    try:
        result = await service.add_document(
            uuid.UUID(topic_id),
            uuid.UUID(body.document_id),
            user_id,
            is_primary=body.is_primary,
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TOPIC_ADD_DOCUMENT_FAILED",
        )
    return result


@router.delete(
    "/{topic_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove document from topic",
)
async def remove_document(
    topic_id: str,
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Remove a document from this topic."""
    service = TopicService(db)
    success = await service.remove_document(
        uuid.UUID(topic_id), uuid.UUID(document_id), user_id
    )
    if not success:
        raise AppError(
            message="Topic or document not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_REMOVE_DOCUMENT_FAILED",
        )
    return None


@router.post(
    "/{topic_id}/notes",
    status_code=status.HTTP_201_CREATED,
    summary="Add note to topic",
)
async def add_note(
    topic_id: str,
    body: AddNoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Add a note to this topic."""
    service = TopicService(db)
    try:
        result = await service.add_note(
            uuid.UUID(topic_id), uuid.UUID(body.note_id), user_id
        )
    except ValueError as e:
        raise AppError(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TOPIC_ADD_NOTE_FAILED",
        )
    return result


@router.delete(
    "/{topic_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove note from topic",
)
async def remove_note(
    topic_id: str,
    note_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Remove a note from this topic."""
    service = TopicService(db)
    success = await service.remove_note(
        uuid.UUID(topic_id), uuid.UUID(note_id), user_id
    )
    if not success:
        raise AppError(
            message="Topic or note not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TOPIC_REMOVE_NOTE_FAILED",
        )
    return None


@router.get(
    "/{topic_id}/documents",
    summary="Get topic documents",
)
async def get_topic_documents(
    topic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List all documents in this topic."""
    service = TopicService(db)
    docs = await service.get_topic_documents(uuid.UUID(topic_id), user_id)
    return {
        "topic_id": topic_id,
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "status": d.status.value,
                "created_at": str(d.created_at),
            }
            for d in docs
        ],
        "count": len(docs),
    }


@router.get(
    "/{topic_id}/notes",
    summary="Get topic notes",
)
async def get_topic_notes(
    topic_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List all notes in this topic."""
    service = TopicService(db)
    notes = await service.get_topic_notes(uuid.UUID(topic_id), user_id)
    return {
        "topic_id": topic_id,
        "notes": [
            {
                "id": str(n.id),
                "title": n.title,
                "note_type": n.note_type,
                "created_at": str(n.created_at),
            }
            for n in notes
        ],
        "count": len(notes),
    }
