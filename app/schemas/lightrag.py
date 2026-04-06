from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class ExtractedEntity(BaseModel):
    name: str = Field(..., description="The canonical name of the entity.")
    entity_type: str = Field(..., description="The type of the entity (e.g., PERSON, ORGANIZATION, CONCEPT).")
    description: str = Field(..., description="A brief description of the entity.")
    confidence: float = Field(default=0.5, ge=0, le=100.0)

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
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

class GraphNodeView(BaseModel):
    id: str  # Entity name làm ID
    label: str
    type: str
    description: Optional[str] = None

class GraphEdgeView(BaseModel):
    id: str  # Database UUID của relation làm Edge ID
    source: str
    target: str
    label: str
    description: Optional[str] = None
