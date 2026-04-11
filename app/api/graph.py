from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..repositories.graph_repo import GraphRepository
from ..repositories.document_repo import DocumentRepository
from ..core.retriever import Retriever
from ..services.llm_service import llm_service
from ..services.cross_verification_service import cross_verification_service
from ..services.entity_alias_service import get_alias_resolution_service, EntityAliasResolutionService
from ..services.backlink_service import BacklinkService
from ..services.tag_service import TagService
from ..services.entity_resolution_service import EntityResolutionService
from ..schemas.lightrag import (
    QueryRequest,
    QueryResponse,
    GraphNodeView,
    GraphEdgeView,
    GlobalGraphRequest,
    GlobalGraphResponse,
    GlobalGraphNode,
    GlobalGraphEdge,
    MultiDocQueryRequest,
    MultiDocQueryResponse,
    CrossVerificationSummary,
    DocumentGraphResponse,
)
from .dependencies import get_optional_user_id, get_current_user_id
from ..worker.queue import get_redis_pool
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/graph", tags=["graph"])

@router.post("/query", response_model=QueryResponse)
async def query_graph(request: QueryRequest, user_id: Optional[uuid.UUID] = Depends(get_optional_user_id), db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge graph for a specific document or global context.
    """
    if not request.document_id:
        raise HTTPException(status_code=400, detail="Document ID is required for now.")

    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)

    try:
        context, _ = await retriever.retrieve(request.query, request.document_id, user_id=user_id)
        response_text = await retriever.generate(request.query, context)

        return QueryResponse(
            query=request.query,
            response=response_text,
            context_used=context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/view", response_model=DocumentGraphResponse)
async def get_document_graph(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy toàn bộ dữ liệu đồ thị của một tài liệu để hiển thị lên UI (Visualization).
    Trả về danh sách nodes và edges.
    """
    # Validate document tồn tại
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from ..core.graph_builder import get_graph_builder
    import networkx as nx
    builder = get_graph_builder()
    
    # Try to load graph for advanced analysis (communities, positions)
    # We don't fail if load fails, just return raw data
    await builder.load_graph(str(document_id))
    nx_graph = builder.get_graph()
    
    communities = {}
    positions = {}
    
    if nx_graph.number_of_nodes() > 0:
        # 1. Community Detection
        comm_list = await builder.detect_communities(str(document_id))
        for comm in comm_list:
            for node_name in comm["nodes"]:
                communities[node_name] = comm["community_id"]
        
        # 2. Layout Positioning (Spring Layout)
        # We only do this if there are nodes and it's not too large
        if 0 < nx_graph.number_of_nodes() < 500:
            try:
                # Use a simple spring layout as a hint for the frontend
                pos_dict = nx.spring_layout(nx_graph, k=0.15, iterations=50)
                positions = {name: {"x": float(p[0]) * 500, "y": float(p[1]) * 500} for name, p in pos_dict.items()}
            except:
                pass

    # 3. Load from Database
    repo = GraphRepository(db)
    entities = await repo.get_all_entities(document_id)
    relations = await repo.get_all_relations(document_id)
    
    nodes = [
        GraphNodeView(
            id=e.canonical_name,
            db_id=str(e.id),
            label=e.canonical_name,
            type=e.entity_type,
            description=e.description,
            source=e.source,
            tags=e.tags,
            file_path=e.file_path,
            metadata=e.metadata_,
            community=communities.get(e.canonical_name),
            x=positions.get(e.canonical_name, {}).get("x"),
            y=positions.get(e.canonical_name, {}).get("y")
        ) for e in entities
    ]

    edges = [
        GraphEdgeView(
            id=str(r.id),
            source=r.source_entity.canonical_name,
            target=r.target_entity.canonical_name,
            label=r.relation_type,
            description=r.description
        ) for r in relations
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "communities_count": len(comm_list) if 'comm_list' in locals() else 0
        }
    }

@router.get("/{document_id}/stats")
async def get_graph_stats(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thống kê về số lượng thực thể và quan hệ đã trích xuất được từ tài liệu.
    """
    # Validate document tồn tại
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    repo = GraphRepository(db)
    e_count = await repo.count_entities(document_id)
    r_count = await repo.count_relations(document_id)

    return {
        "entity_count": e_count,
        "relation_count": r_count
    }


@router.get("/{document_id}/centrality")
async def get_graph_centrality(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get centrality scores (degree, betweenness, closeness) for entities in the document graph.
    """
    from ..core.graph_builder import get_graph_builder
    builder = get_graph_builder()
    
    # Load graph from storage
    success = await builder.load_graph(str(document_id))
    if not success:
        # Fallback: maybe the graph hasn't been persisted yet?
        # In a real scenario, we might want to rebuild it from DB or return 404
        raise HTTPException(status_code=404, detail="Graph not found for this document")

    scores = await builder.get_centrality_scores(str(document_id))
    return scores


@router.get("/{document_id}/export")
async def export_graph(
    document_id: uuid.UUID,
    format: str = "graphml",
    db: AsyncSession = Depends(get_db)
):
    """
    Export the graph in various formats (graphml, json).
    """
    from ..core.graph_builder import get_graph_builder
    from fastapi.responses import Response, StreamingResponse
    import io
    
    builder = get_graph_builder()
    success = await builder.load_graph(str(document_id))
    if not success:
        raise HTTPException(status_code=404, detail="Graph not found")

    if format == "graphml":
        import networkx as nx
        output = io.StringIO()
        nx.write_graphml(builder.get_graph(), output)
        return Response(
            content=output.getvalue(),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=graph_{document_id}.graphml"}
        )
    elif format == "json":
        data = builder._graph_to_dict()
        return data
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


# =============================================
# Sprint 4: Global Graph Explorer & Multi-doc Query APIs
# =============================================

@router.post("/global", response_model=GlobalGraphResponse)
async def get_global_graph(
    request: GlobalGraphRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated knowledge graph across multiple documents.

    - **scope**: "user_global" (all user's docs) or "selected" (specific docs)
    - **document_ids**: List of doc UUIDs (only when scope="selected")
    - **top_k**: Max entities to include (10-500)
    - **min_confidence**: Filter entities by confidence threshold

    Returns React Flow-compatible nodes/edges with aggregation metadata.
    """
    graph_repo = GraphRepository(db)

    # Determine which documents to include
    if request.scope == "selected" and request.document_ids:
        doc_ids = [uuid.UUID(d) for d in request.document_ids]
    else:
        # Get all user's documents
        doc_repo = DocumentRepository(db)
        docs = await doc_repo.get_by_user(user_id, skip=0, limit=100)
        doc_ids = [d.id for d in docs]

    if not doc_ids:
        return GlobalGraphResponse(
            nodes=[],
            edges=[],
            total_documents=0,
            total_entities=0,
            total_relations=0,
            scope=request.scope,
        )

    # Aggregate entities across documents
    all_entities = {}  # canonical_name -> {entity_type, description, docs[], confidences[]}
    all_relations = {}  # (source, target, relation_type) -> {description, docs[]}

    for doc_id in doc_ids:
        # Get entities
        entities = await graph_repo.get_all_entities(doc_id)
        for entity in entities:
            if entity.confidence < request.min_confidence:
                continue

            name = entity.canonical_name
            if name not in all_entities:
                all_entities[name] = {
                    "entity_type": entity.entity_type,
                    "description": entity.description,
                    "documents": [],
                    "confidences": [],
                    "occurrences": 0,
                }
            
            all_entities[name]["documents"].append(str(doc_id))
            all_entities[name]["confidences"].append(entity.confidence)
            all_entities[name]["occurrences"] += 1

            # Keep best description (highest confidence)
            if entity.description:
                current_best_conf = all_entities[name].get("best_confidence", 0)
                if entity.confidence > current_best_conf:
                    all_entities[name]["description"] = entity.description
                    all_entities[name]["best_confidence"] = entity.confidence

        # Get relations
        relations = await graph_repo.get_all_relations(doc_id)
        for rel in relations:
            key = (rel.source_entity.canonical_name, rel.target_entity.canonical_name, rel.relation_type)
            if key not in all_relations:
                all_relations[key] = {
                    "description": rel.description,
                    "documents": [],
                    "frequency": 0,
                }

            all_relations[key]["documents"].append(str(doc_id))
            all_relations[key]["frequency"] += 1
            if rel.description:
                all_relations[key]["description"] = rel.description

    # Sort and limit entities
    sorted_entities = sorted(
        all_entities.items(),
        key=lambda x: x[1]["occurrences"],
        reverse=True
    )[:request.top_k]

    # Build nodes
    nodes = []
    for name, data in sorted_entities:
        nodes.append(GlobalGraphNode(
            id=name,
            label=name,
            entity_type=data["entity_type"],
            description=data["description"],
            document_count=len(set(data["documents"])),
            total_occurrences=data["occurrences"],
            avg_confidence=round(sum(data["confidences"]) / len(data["confidences"]), 3),
        ))

    # Build edges (only include edges between included nodes)
    node_names = set(name for name, _ in sorted_entities)
    edges = []
    for (source, target, rel_type), data in all_relations.items():
        if source in node_names and target in node_names:
            edges.append(GlobalGraphEdge(
                id=f"{source}--{rel_type}--{target}",
                source=source,
                target=target,
                label=rel_type,
                description=data["description"],
                frequency=data["frequency"],
                documents=list(set(data["documents"])),
            ))

    return GlobalGraphResponse(
        nodes=nodes,
        edges=edges,
        total_documents=len(set(doc_ids)),
        total_entities=len(nodes),
        total_relations=len(edges),
        scope=request.scope,
    )


@router.post("/query-multi", response_model=MultiDocQueryResponse)
async def query_multiple_documents(
    request: MultiDocQueryRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Query across multiple documents with cross-verification.

    - **query**: User's question
    - **document_ids**: Optional list of doc UUIDs. If None, searches all user docs.
    - **scope**: "document" (scoped) or "user_global" (all docs)
    - **enable_cross_verification**: Enable LLM contradiction detection

    Returns synthesized answer with source attribution and contradiction analysis.
    """
    graph_repo = GraphRepository(db)
    retriever = Retriever(graph_repo)

    # Multi-document retrieval
    context, entity_names, cross_verification = await retriever.retrieve_multi(
        query=request.query,
        user_id=str(user_id),
        document_ids=request.document_ids,
        scope=request.scope,
    )

    # Generate response with context
    context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])
    
    prompt = f"""Answer the question based ONLY on the provided context.
If context contains information from multiple documents, synthesize the answer and mention sources.

Context:
{context_str}

Question: {request.query}

Answer:
"""

    response_text = await llm_service.get_chat_completion([
        {"role": "user", "content": prompt}
    ])
    response_content = response_text.choices[0].message.content

    # Determine documents involved
    doc_ids_involved = list(set([
        ctx.get("metadata", {}).get("document_id", "unknown")
        for ctx in context
        if ctx.get("metadata", {}).get("document_id")
    ]))

    # Build cross-verification summary if enabled
    cross_ver_summary = None
    if request.enable_cross_verification and len(doc_ids_involved) >= 2:
        # Prepare document contexts for cross-verification
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
        cv_result = await cross_verification_service.cross_check(
            query=request.query,
            document_contexts=list(doc_contexts.values()),
        )

        cross_ver_summary = CrossVerificationSummary(**cv_result)

    return MultiDocQueryResponse(
        query=request.query,
        response=response_content,
        context_used=context[:20],  # Limit context size
        cross_verification=cross_ver_summary,
        documents_involved=doc_ids_involved,
    )


# =============================================
# Entity Alias Resolution APIs
# =============================================

@router.get("/entities/aliases")
async def list_entity_aliases(
    user_id: uuid.UUID = Depends(get_current_user_id),
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List user's entity aliases."""
    alias_service = get_alias_resolution_service(db)
    aliases = await alias_service.get_user_aliases(user_id, skip=skip, limit=limit)
    
    return {
        "aliases": [
            {
                "alias_name": a.alias_name,
                "canonical_name": a.canonical_name,
                "confidence": a.confidence,
                "source": a.source,
                "created_at": a.created_at,
            }
            for a in aliases
        ],
        "total": len(aliases),
    }


@router.post("/entities/resolve-alias")
async def resolve_entity_alias(
    alias_name: str,
    suggested_canonical: Optional[str] = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve an entity alias to canonical name.
    If suggested_canonical provided, creates alias after LLM verification.
    """
    alias_service = get_alias_resolution_service(db)

    # Resolve alias
    canonical = await alias_service.resolve_entity_alias(
        entity_name=alias_name,
        user_id=user_id,
        suggested_canonical=suggested_canonical,
    )

    if not canonical:
        return {
            "alias_name": alias_name,
            "resolved": False,
            "message": "No canonical entity found or alias not verified.",
        }

    return {
        "alias_name": alias_name,
        "canonical_name": canonical,
        "resolved": True,
    }


@router.post("/entities/suggest-aliases")
async def suggest_entity_aliases(
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-suggested entity aliases for user review.

    Finds entities with similar names that might be aliases of the same concept.
    """
    alias_service = get_alias_resolution_service(db)
    suggestions = await alias_service.suggest_aliases(user_id, limit=limit)
    
    return {
        "suggestions": suggestions,
        "total": len(suggestions),
    }


@router.post("/entities/create-alias")
async def create_entity_alias(
    alias_name: str,
    canonical_name: str,
    source: str = "manual",
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually create an entity alias.

    - **alias_name**: The alias to create (e.g., "AI")
    - **canonical_name**: The canonical entity name (e.g., "Artificial Intelligence")
    - **source**: "manual" | "ai_suggested" | "auto"
    """
    alias_service = get_alias_resolution_service(db)

    result = await alias_service.create_alias(
        user_id=user_id,
        alias_name=alias_name,
        canonical_name=canonical_name,
        source=source,
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Alias already exists or canonical entity not found.",
        )

    return {
        "alias_name": result.alias_name,
        "canonical_name": result.canonical_name,
        "confidence": result.confidence,
        "source": result.source,
    }


@router.get("/global-entities")
async def get_global_entities(
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated entities across all user's documents.

    Returns entities grouped by canonical_name with:
    - document_count: How many docs mention this entity
    - avg_confidence: Average confidence score
    - total_occurrences: Total appearances across all docs
    """
    alias_service = get_alias_resolution_service(db)
    global_entities = await alias_service.get_global_entities(user_id, limit=limit)
    
    return {
        "entities": global_entities,
        "total": len(global_entities),
    }

# =============================================
# Obsidian Integration APIs
# =============================================

class ObsidianImportRequest(BaseModel):
    vault_path: str

@router.post("/import/obsidian")
async def import_obsidian_vault(
    request: ObsidianImportRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Start a background task to import an Obsidian Vault.
    Returns the job ID to track progress.
    """
    redis_pool = await get_redis_pool()
    job_id = str(uuid.uuid4())
    
    await redis_pool.enqueue_job(
        "import_obsidian_vault_task",
        request.vault_path,
        str(user_id),
        job_id,
        _job_id=f"obsidian_import:{job_id}"
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Obsidian import task has been queued."
    }

@router.get("/import/obsidian/status/{job_id}")
async def get_obsidian_import_status(
    job_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Check the status of an Obsidian import job.
    """
    redis_pool = await get_redis_pool()
    progress_key = f"import:{job_id}:progress"
    
    status_data = await redis_pool.get(progress_key)
    if not status_data:
        return {"status": "not_found"}
    
    import json
    try:
        return json.loads(status_data)
    except:
        return {"status": status_data}

# =============================================
# Backlinks, Tags & Entity Resolution APIs
# =============================================

@router.get("/entities/{entity_id}/backlinks")
async def get_entity_backlinks(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách các liên kết ngược (incoming relations) của một thực thể.
    """
    service = BacklinkService(db)
    return await service.get_backlinks(entity_id)

@router.get("/tags")
async def get_all_graph_tags(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách tất cả các thẻ (tags) trong đồ thị tri thức của người dùng.
    """
    service = TagService(db)
    return await service.get_all_tags(user_id)

@router.get("/tags/{tag}/entities")
async def get_entities_by_tag(
    tag: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách các thực thể theo thẻ (tag).
    """
    service = TagService(db)
    return await service.get_entities_by_tag(tag, user_id)

@router.get("/duplicates")
async def get_potential_duplicate_entities(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Tìm kiếm các thực thể có khả năng trùng lặp để người dùng xem xét gộp.
    """
    service = EntityResolutionService(db)
    return await service.get_potential_duplicates(user_id)

class MergeEntitiesRequest(BaseModel):
    primary_entity_id: uuid.UUID
    secondary_entity_id: uuid.UUID

@router.post("/entities/merge")
async def merge_entities(
    request: MergeEntitiesRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Gộp hai thực thể lại thành một. Toàn bộ quan hệ sẽ được chuyển hướng về thực thể chính.
    """
    service = EntityResolutionService(db)
    try:
        merged_entity = await service.merge_entities(
            user_id=user_id,
            primary_id=request.primary_entity_id,
            secondary_id=request.secondary_entity_id
        )
        await db.commit()
        return {
            "status": "success", 
            "message": f"Thực thể đã được gộp thành công vào '{merged_entity.canonical_name}'",
            "primary_id": str(merged_entity.id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi gộp thực thể: {str(e)}")

