"""
Note API endpoints for Stage 2 - Zettelkasten & Bi-directional Linking

Endpoints:
- POST   /api/v1/notes              - Tạo note mới
- GET    /api/v1/notes              - List user's notes (paginate, filter)
- GET    /api/v1/notes/graph        - Note graph cho visualization
- GET    /api/v1/notes/search       - Search notes by tags/content
- GET    /api/v1/notes/{id}         - Note detail + backlinks
- PATCH  /api/v1/notes/{id}         - Cập nhật note
- DELETE /api/v1/notes/{id}         - Xóa note
- POST   /api/v1/notes/{id}/links   - Tạo link thủ công
- GET    /api/v1/notes/{id}/backlinks - Danh sách backlinks
- POST   /api/v1/notes/{id}/suggest-backlinks - AI gợi ý backlinks
"""

import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.api.dependencies import get_current_user_id
from app.repositories.note_repo import NoteRepository, NoteLinkRepository
from app.repositories.note_entity_link_repo import NoteEntityLinkRepository
from app.repositories.graph_repo import GraphRepository
from app.services.note_service import NoteService
from app.services.backlink_ai_service import BacklinkAIService
from app.services.llm_service import LLMService
from app.schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteRead,
    NoteDetail,
    NoteListItem,
    NoteListResponse,
    NoteLinkCreate,
    NoteLinkResponse,
    BacklinkSuggestionsResponse,
    NoteGraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])


def get_note_service(db: AsyncSession) -> NoteService:
    """Dependency injector cho NoteService."""
    llm_service = LLMService()
    note_repo = NoteRepository(db)
    note_link_repo = NoteLinkRepository(db)
    graph_repo = GraphRepository(db)
    # P1-2: Tạo repository cho auto entity linking
    note_entity_link_repo = NoteEntityLinkRepository(db)
    
    backlink_ai_service = BacklinkAIService(
        llm_service=llm_service,
        note_repo=note_repo,
        note_link_repo=note_link_repo,
        graph_repo=graph_repo,
    )
    return NoteService(
        note_repo=note_repo,
        note_link_repo=note_link_repo,
        backlink_ai_service=backlink_ai_service,
        # P1-2: Inject dependencies
        note_entity_link_repo=note_entity_link_repo,
    )


# ===== Note CRUD =====

@router.post("", response_model=NoteRead, status_code=201)
async def create_note(
    request: NoteCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo atomic note mới trong Zettelkasten.

    Note types:
    - fleeting: Ý tưởng nhanh, tạm thời
    - literature: Ghi chú từ tài liệu/đọc
    - permanent: Kiến thức cốt lõi, dài hạn
    - project: Ghi chú dự án cụ thể

    BR-009: Auto entity linking được trigger khi tạo note.
    Backlink suggestions được enqueue dưới background task.
    """
    service = get_note_service(db)

    note = await service.create_note(
        user_id=user_id,
        title=request.title,
        content=request.content,
        note_type=request.note_type,
        tags=request.tags,
        metadata=request.metadata,
    )

    # BR-009: Enqueue backlink suggestions dưới background (KHÔNG block response)
    if background_tasks:
        background_tasks.add_task(
            _enqueue_backlink_suggestions,
            note_id=note.id,
            user_id=user_id,
        )

    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    request: NoteUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Cập nhật note (title, content, tags, note_type).

    BR-009: Nếu content thay đổi → auto re-run entity linking + backlink suggestions.
    """
    service = get_note_service(db)

    note = await service.update_note(
        note_id=note_id,
        user_id=user_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        note_type=request.note_type,
    )

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # BR-009: Re-enqueue backlink suggestions nếu content thay đổi
    if background_tasks and request.content is not None:
        background_tasks.add_task(
            _enqueue_backlink_suggestions,
            note_id=note.id,
            user_id=user_id,
        )

    return NoteRead.model_validate(note)


async def _enqueue_backlink_suggestions(note_id: uuid.UUID, user_id: uuid.UUID):
    """
    Background task: AI-suggest backlinks và auto-create links nếu confidence cao.
    """
    try:
        from app.database import set_current_user_id

        async with AsyncSessionLocal() as session:
            # Set RLS context for background task
            await set_current_user_id(session, str(user_id))

            service = get_note_service(session)
            suggestions = await service.suggest_backlinks(note_id, user_id)

            # Auto-create note-to-note links nếu confidence >= threshold
            from app.constants import NOTE_LINK_SUGGESTION_THRESHOLD
            note_link_repo = NoteLinkRepository(session)

            for related_note in suggestions.get("related_notes", []):
                if related_note.get("confidence", 0) >= NOTE_LINK_SUGGESTION_THRESHOLD:
                    # Check nếu link đã tồn tại
                    existing = await note_link_repo.get_link(
                        source_note_id=note_id,
                        target_note_id=related_note["note_id"],
                        user_id=user_id,
                    )
                    if not existing:
                        await note_link_repo.create_link(
                            user_id=user_id,
                            source_note_id=note_id,
                            target_note_id=related_note["note_id"],
                            context=related_note.get("context", ""),
                            link_type="ai_suggested",
                        )
                        await session.commit()
                        logger.info(
                            f"Auto-linked note {note_id} → {related_note['note_id']} "
                            f"(confidence={related_note['confidence']:.2f})"
                        )
    except Exception as e:
        logger.warning(f"Background backlink suggestion failed for note {note_id}: {e}")


@router.get("", response_model=NoteListResponse)
async def list_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    note_type: Optional[str] = Query(None, description="Filter by note type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's notes với phân trang và filter.

    - `tags`: Comma-separated list (ví dụ: "python,ml,ai")
    - `note_type`: fleeting | literature | permanent | project
    """
    service = get_note_service(db)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    notes, total = await service.list_notes(
        user_id=user_id,
        skip=skip,
        limit=limit,
        note_type=note_type,
        tags=tag_list,
    )

    return NoteListResponse(
        notes=[NoteListItem.model_validate(n) for n in notes],
        total=total,
    )


# ===== Graph & Search (static routes BEFORE /{note_id}) =====

@router.get("/graph", response_model=NoteGraphResponse)
async def get_note_graph(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy toàn bộ note graph cho Zettelkasten Graph View.

    Response dùng cho React Flow visualization:
    - Nodes: Notes (color-coded theo note_type)
    - Edges: NoteLinks (thickness theo link_type)
    """
    service = get_note_service(db)

    graph_data = await service.get_note_graph(user_id)
    return NoteGraphResponse(**graph_data)


@router.get("/search", response_model=NoteListResponse)
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query (title/content/tags)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Search notes by title/content (ILIKE).
    """
    service = get_note_service(db)

    # Search by content
    notes, total = await service.note_repo.search_by_content(
        user_id=user_id, query_text=q, skip=skip, limit=limit
    )

    return NoteListResponse(
        notes=[NoteListItem.model_validate(n) for n in notes],
        total=total,
    )


# ===== Note Detail / Update / Delete (path parameter routes) =====

@router.get("/{note_id}", response_model=NoteDetail)
async def get_note_detail(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy chi tiết note với backlinks (incoming/outgoing links).
    """
    service = get_note_service(db)

    note = await service.get_note_detail(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return NoteDetail.model_validate(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Xóa note (cascades to links)."""
    service = get_note_service(db)
    success = await service.delete_note(note_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")


# ===== Note Links =====

@router.post("/{note_id}/links", response_model=NoteLinkResponse)
async def create_note_link(
    note_id: uuid.UUID,
    request: NoteLinkCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo link thủ công giữa 2 notes.

    - `note_id`: Source note (note đang xem)
    - `target_note_id`: Target note (note muốn link tới)
    - `context`: Giải thích tại sao link (optional)
    """
    service = get_note_service(db)

    link = await service.create_link(
        user_id=user_id,
        source_note_id=note_id,
        target_note_id=request.target_note_id,
        context=request.context,
        link_type="manual",
    )

    if not link:
        raise HTTPException(
            status_code=400,
            detail="Cannot create link. Check if both notes exist and belong to you.",
        )

    return NoteLinkResponse.model_validate(link)


@router.get("/{note_id}/backlinks", response_model=List[NoteLinkResponse])
async def get_backlinks(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách backlinks (incoming links) của một note.
    """
    service = get_note_service(db)

    backlinks = await service.get_backlinks(note_id, user_id)
    return [NoteLinkResponse.model_validate(link) for link in backlinks]


# ===== AI Suggestions =====

@router.post("/{note_id}/suggest-backlinks", response_model=BacklinkSuggestionsResponse)
async def suggest_backlinks(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    AI gợi ý backlinks cho note.

    Quét nội dung note và tìm:
    1. Related graph entities từ Knowledge Graph
    2. Related notes khác trong Zettelkasten

    Threshold: NOTE_LINK_SUGGESTION_THRESHOLD = 0.75
    """
    service = get_note_service(db)

    suggestions = await service.suggest_backlinks(note_id, user_id)
    return BacklinkSuggestionsResponse(**suggestions)
