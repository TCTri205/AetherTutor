from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..repositories.graph_repo import GraphRepository
from ..repositories.document_repo import DocumentRepository
from ..core.retriever import Retriever
from ..services.llm_service import llm_service
from ..services.cross_verification_service import cross_verification_service
from ..services.entity_alias_service import get_alias_resolution_service
from ..services.backlink_service import BacklinkService
from ..services.tag_service import TagService
from ..services.entity_resolution_service import EntityResolutionService
from ..core.visualizer_agent import get_visualizer_agent
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
    MermaidRequest,
    MermaidResponse,
    MermaidMetadata,
    EntityCreateRequest,
    EntityUpdateRequest,
    EntityResponse,
    RelationCreateRequest,
    RelationResponse,
)
from .dependencies import get_optional_user_id, get_current_user_id
from ..worker.queue import get_redis_pool
from ..core.exceptions import DuplicateResourceError, ResourceNotFoundError
from ..core.graph_cache import get_graph_cache
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
    from fastapi.responses import Response
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


# =============================================
# Sprint 8: Mermaid Diagram Generation
# =============================================

@router.post("/mermaid", response_model=MermaidResponse)
async def generate_mermaid_diagram(
    request: MermaidRequest,
    user_id: Optional[uuid.UUID] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate Mermaid diagram từ Knowledge Graph.

    Supports 3 formats:
    - mindmap: Sơ đồ tư duy cho phân tích chủ đề
    - flowchart_td: Flowchart top-down cho quy trình
    - flowchart_lr: Flowchart left-right cho mối quan hệ

    Có thể chọn topic cụ thể để trích xuất subgraph, hoặc lấy toàn bộ graph.
    """
    try:
        # Lấy graph data từ database
        graph_repo = GraphRepository(db)
        visualizer = get_visualizer_agent()

        # Xác định document_id
        doc_id = None
        if request.document_id:
            try:
                doc_id = uuid.UUID(request.document_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document_id format")

        # Nếu có document_id cụ thể
        if doc_id:
            # Validate document tồn tại và thuộc về user
            if user_id:
                doc_repo = DocumentRepository(db)
                doc = await doc_repo.get_by_id(doc_id)
                if not doc:
                    raise HTTPException(status_code=404, detail="Document not found")
                # User isolation check
                if hasattr(doc, 'user_id') and doc.user_id != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied: Document belongs to another user"
                    )

            # Lấy entities và relations từ document
            entities = await graph_repo.get_all_entities_for_document(doc_id)
            relations = await graph_repo.get_all_relations_for_document(doc_id)

            # Convert sang format cho visualizer
            nodes = [
                {
                    "id": str(entity.id),
                    "name": entity.canonical_name,
                    "type": entity.entity_type,
                    "description": entity.description,
                    "confidence": entity.confidence,
                }
                for entity in entities
            ]

            # Build node_id map để resolve source/target
            entity_id_map = {str(e.id): e.canonical_name for e in entities}

            edges = []
            for rel in relations:
                source_name = entity_id_map.get(str(rel.source_entity_id))
                target_name = entity_id_map.get(str(rel.target_entity_id))
                if source_name and target_name:
                    edges.append({
                        "source": str(rel.source_entity_id),
                        "target": str(rel.target_entity_id),
                        "label": rel.relation_type,
                        "description": rel.description,
                    })

            graph_data = {"nodes": nodes, "edges": edges}

        else:
            # Global graph: lấy tất cả entities/relations của user
            if not user_id:
                raise HTTPException(
                    status_code=400,
                    detail="user_id required for global graph. Provide document_id or authenticate."
                )

            entities = await graph_repo.get_user_entities(user_id)
            relations = await graph_repo.get_user_relations(user_id)

            nodes = [
                {
                    "id": str(entity.id),
                    "name": entity.canonical_name,
                    "type": entity.entity_type,
                    "description": entity.description,
                    "confidence": entity.confidence,
                    "document_id": str(entity.document_id),
                }
                for entity in entities
            ]

            entity_id_map = {str(e.id): e.canonical_name for e in entities}
            edges = []
            for rel in relations:
                source_name = entity_id_map.get(str(rel.source_entity_id))
                target_name = entity_id_map.get(str(rel.target_entity_id))
                if source_name and target_name:
                    edges.append({
                        "source": str(rel.source_entity_id),
                        "target": str(rel.target_entity_id),
                        "label": rel.relation_type,
                        "description": rel.description,
                    })

            graph_data = {"nodes": nodes, "edges": edges}

        # Generate Mermaid diagram
        result = await visualizer.generate_mermaid(
            graph_data=graph_data,
            topic=request.topic,
            max_nodes=request.max_nodes,
            max_depth=request.max_depth,
            format=request.format,
        )

        return MermaidResponse(
            mermaid_code=result["mermaid_code"],
            metadata=MermaidMetadata(
                total_nodes=result["metadata"]["total_nodes"],
                total_edges=result["metadata"]["total_edges"],
                truncated=result["metadata"]["truncated"],
                format=result["metadata"]["format"],
                document_id=request.document_id,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating Mermaid diagram: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo diagram: {str(e)}")


# =========================================================================
# Stage 3: Interactive Graph Editing — CRUD Endpoints
# =========================================================================

def _entity_to_response(entity) -> EntityResponse:
    """Convert GraphEntity model to EntityResponse schema."""
    return EntityResponse(
        id=entity.id,
        document_id=entity.document_id,
        user_id=entity.user_id,
        canonical_name=entity.canonical_name,
        entity_type=entity.entity_type,
        description=entity.description or "",
        confidence=entity.confidence,
        source=entity.source or "manual",
        tags=entity.tags or [],
        metadata=entity.metadata_ or {},
        version=entity.version,
        created_at=entity.created_at,
        updated_at=getattr(entity, 'updated_at', entity.created_at),
    )


def _relation_to_response(relation) -> RelationResponse:
    """Convert GraphRelation model to RelationResponse schema."""
    return RelationResponse(
        id=relation.id,
        document_id=relation.document_id,
        source_entity_id=relation.source_entity_id,
        target_entity_id=relation.target_entity_id,
        relation_type=relation.relation_type,
        description=relation.description or "",
        source=relation.source or "manual",
        version=relation.version,
        created_at=relation.created_at,
        updated_at=getattr(relation, 'updated_at', relation.created_at),
    )


@router.post(
    "/entities",
    response_model=EntityResponse,
    status_code=201,
    summary="Create a new graph entity",
)
async def create_entity(
    request: EntityCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new graph entity for the authenticated user.

    Validates:
    - Entity name must be unique within the document
    - User must own the document
    """
    graph_repo = GraphRepository(db)

    # TODO: Validate user owns document_id (need document_repo check)
    # For now, we trust the user_id passed in

    try:
        entity_data = {
            "canonical_name": request.canonical_name,
            "entity_type": request.entity_type,
            "description": request.description,
            "confidence": request.confidence,
            "source": request.source,
            "tags": request.tags,
            "metadata": request.metadata,
        }

        # We need a document_id — for now, use the first document of the user
        # In production, this should be explicitly passed or derived
        from ..repositories.document_repo import DocumentRepository
        doc_repo = DocumentRepository(db)
        user_docs = await doc_repo.get_user_documents(user_id)
        if not user_docs:
            raise HTTPException(status_code=400, detail="User has no documents. Create a document first.")

        document_id = user_docs[0].id

        entity = await graph_repo.create_entity(
            entity_data=entity_data,
            user_id=user_id,
            document_id=document_id,
        )

        # Audit log
        await graph_repo.log_edit(
            user_id=user_id,
            action="CREATE",
            entity_type="entity",
            document_id=document_id,
            entity_id=entity.id,
            new_value=entity_data,
        )

        # Invalidate cache
        await get_graph_cache().invalidate(document_id)

        return _entity_to_response(entity)

    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="Update an existing graph entity",
)
async def update_entity(
    entity_id: uuid.UUID,
    request: EntityUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing graph entity with optimistic concurrency control.

    Requires:
    - expected_version: current version number (for conflict detection)
    """
    graph_repo = GraphRepository(db)

    try:
        # Build updates dict (only non-None fields)
        updates = {k: v for k, v in request.model_dump(exclude_unset=True).items() if k != "expected_version"}

        if not updates:
            raise HTTPException(status_code=400, detail="No update fields provided")

        entity = await graph_repo.update_entity(
            entity_id=entity_id,
            updates=updates,
            expected_version=request.expected_version,
            user_id=user_id,
        )

        # Audit log
        await graph_repo.log_edit(
            user_id=user_id,
            action="UPDATE",
            entity_type="entity",
            document_id=entity.document_id,
            entity_id=entity_id,
            new_value=updates,
        )

        # Invalidate cache
        await get_graph_cache().invalidate(entity.document_id)

        return _entity_to_response(entity)

    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=409,
            detail=e.message,
            headers={"X-Current-Version": str(e.details.get("current_version", 0))} if e.details else None,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/entities/{entity_id}",
    status_code=204,
    summary="Delete a graph entity",
)
async def delete_entity(
    entity_id: uuid.UUID,
    expected_version: int = Query(..., ge=1, description="Optimistic concurrency version"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a graph entity.

    Cascade: all relations involving this entity will be deleted (FK constraint).
    """
    graph_repo = GraphRepository(db)

    try:
        # Get entity info for audit log and cache invalidation
        from sqlalchemy import select as sa_select
        from ..models.graph import GraphEntity as GraphEntityModel
        result = await db.execute(
            sa_select(GraphEntityModel).where(GraphEntityModel.id == entity_id)
        )
        entity = result.scalar_one_or_none()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        await graph_repo.delete_entity(
            entity_id=entity_id,
            expected_version=expected_version,
            user_id=user_id,
        )

        # Audit log
        await graph_repo.log_edit(
            user_id=user_id,
            action="DELETE",
            entity_type="entity",
            document_id=entity.document_id,
            entity_id=entity_id,
        )

        # Invalidate cache
        await get_graph_cache().invalidate(entity.document_id)

        return None

    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/relations",
    response_model=RelationResponse,
    status_code=201,
    summary="Create a new graph relation",
)
async def create_relation(
    request: RelationCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new graph relation (edge) between two entities.

    Validates:
    - Source and target entities must exist and belong to the user
    - Cannot create self-referential relations (source != target)
    """
    graph_repo = GraphRepository(db)

    try:
        # Get document_id from source entity
        from ..models.graph import GraphEntity as GraphEntityModel
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(GraphEntityModel.document_id).where(GraphEntityModel.id == request.source_entity_id)
        )
        doc_row = result.scalar_one_or_none()
        if not doc_row:
            raise HTTPException(status_code=404, detail="Source entity not found")
        document_id = doc_row

        relation_data = {
            "source_entity_id": request.source_entity_id,
            "target_entity_id": request.target_entity_id,
            "relation_type": request.relation_type,
            "description": request.description,
            "source": request.source,
        }

        relation = await graph_repo.create_relation(
            relation_data=relation_data,
            user_id=user_id,
            document_id=document_id,
        )

        # Audit log
        await graph_repo.log_edit(
            user_id=user_id,
            action="CREATE",
            entity_type="relation",
            document_id=document_id,
            relation_id=relation.id,
            new_value=relation_data,
        )

        # Invalidate cache
        await get_graph_cache().invalidate(document_id)

        return _relation_to_response(relation)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/relations/{relation_id}",
    status_code=204,
    summary="Delete a graph relation",
)
async def delete_relation(
    relation_id: uuid.UUID,
    expected_version: int = Query(..., ge=1, description="Optimistic concurrency version"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a graph relation (edge).
    """
    graph_repo = GraphRepository(db)

    try:
        # Get relation info for audit log and cache invalidation
        from sqlalchemy import select as sa_select
        from ..models.graph import GraphRelation as GraphRelationModel
        result = await db.execute(
            sa_select(GraphRelationModel).where(GraphRelationModel.id == relation_id)
        )
        relation = result.scalar_one_or_none()
        if not relation:
            raise HTTPException(status_code=404, detail="Relation not found")

        await graph_repo.delete_relation(
            relation_id=relation_id,
            expected_version=expected_version,
            user_id=user_id,
        )

        # Audit log
        await graph_repo.log_edit(
            user_id=user_id,
            action="DELETE",
            entity_type="relation",
            document_id=relation.document_id,
            relation_id=relation_id,
        )

        # Invalidate cache
        await get_graph_cache().invalidate(relation.document_id)

        return None

    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

