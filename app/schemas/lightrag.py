from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class ExtractedEntity(BaseModel):
    name: str = Field(..., description="The canonical name of the entity.")
    entity_type: str = Field(..., description="The type of the entity (e.g., PERSON, ORGANIZATION, CONCEPT).")
    description: str = Field(..., description="A brief description of the entity.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

class EntityRelation(BaseModel):
    source: str = Field(..., description="The source entity name.")
    target: str = Field(..., description="The target entity name.")
    relation_type: str = Field(..., description="The type of relationship.")
    description: str = Field(..., description="A brief description of the relationship.")

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity]
    relations: List[EntityRelation]

class DocumentIngestRequest(BaseModel):
    content: str
    filename: str

class QueryRequest(BaseModel):
    document_id: Optional[str] = None
    query: str

class QueryResponse(BaseModel):
    query: str
    response: str
    context_used: List[dict] = Field(default_factory=list)

class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str
    message: str

class DocumentDetail(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    processing_step: Optional[str] = None
    entity_count: int = 0
    relation_count: int = 0
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None

class GraphNodeView(BaseModel):
    id: str  # Entity name làm ID
    db_id: Optional[str] = None # Database UUID
    label: str
    type: str
    description: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    file_path: Optional[str] = None
    metadata: Optional[dict] = None
    community: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None

class GraphEdgeView(BaseModel):
    id: str  # Database UUID của relation làm Edge ID
    source: str
    target: str
    label: str
    description: Optional[str] = None

class DocumentGraphResponse(BaseModel):
    nodes: List[GraphNodeView]
    edges: List[GraphEdgeView]
    stats: Optional[dict] = None


# =============================================
# Sprint 4: Global Graph & Multi-doc Schemas
# =============================================

class GlobalGraphRequest(BaseModel):
    """Request for global graph across all user's documents."""
    scope: str = Field(
        default="user_global",
        description="Scope: 'user_global' (all docs) or 'selected' (specific docs)"
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="List of document UUIDs (only used when scope='selected')"
    )
    top_k: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Top K entities to include in graph"
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum entity confidence threshold"
    )


class GlobalGraphNode(BaseModel):
    """Node in global graph (aggregated across documents)."""
    id: str  # Canonical entity name
    label: str
    entity_type: str
    description: Optional[str] = None
    document_count: int = Field(..., description="Number of documents mentioning this entity")
    total_occurrences: int = Field(..., description="Total occurrences across all docs")
    avg_confidence: float = Field(..., description="Average confidence score")
    centrality_score: Optional[float] = Field(default=None, description="Global centrality score")


class GlobalGraphEdge(BaseModel):
    """Edge in global graph."""
    id: str
    source: str
    target: str
    label: str
    description: Optional[str] = None
    frequency: int = Field(..., description="How many times this relation appears across docs")
    documents: List[str] = Field(default_factory=list, description="Document IDs with this relation")


class GlobalGraphResponse(BaseModel):
    """Response for global graph query."""
    nodes: List[GlobalGraphNode]
    edges: List[GlobalGraphEdge]
    total_documents: int
    total_entities: int
    total_relations: int
    scope: str


class MultiDocQueryRequest(BaseModel):
    """Request for multi-document query with cross-verification."""
    query: str
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="List of document UUIDs to query. If None, queries all user docs."
    )
    scope: str = Field(
        default="user_global",
        description="Scope: 'document' (scoped) or 'user_global' (all docs)"
    )
    enable_cross_verification: bool = Field(
        default=True,
        description="Enable LLM-powered cross-document contradiction detection"
    )


class CrossVerificationSummary(BaseModel):
    """Summary of cross-document analysis."""
    documents_analyzed: int
    contradictions: List[dict] = Field(default_factory=list)
    complementary: List[dict] = Field(default_factory=list)
    consensus: List[dict] = Field(default_factory=list)
    consolidated_answer: Optional[str] = None
    claims: List[dict] = Field(default_factory=list)
    disagreements: List[dict] = Field(default_factory=list)


class MultiDocQueryResponse(BaseModel):
    """Response for multi-document query."""
    query: str
    response: str
    context_used: List[dict] = Field(default_factory=list)
    cross_verification: Optional[CrossVerificationSummary] = None
    documents_involved: List[str] = Field(default_factory=list)
