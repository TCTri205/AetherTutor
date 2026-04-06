from fastapi import APIRouter, UploadFile, File, HTTPStatus
from typing import List

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", status_code=HTTPStatus.CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document and start the LightRAG processing pipeline.
    """
    return {"message": f"Document {file.filename} upload started."}

@router.get("/", response_model=List[dict])
async def list_documents():
    """
    List all documents and their processing status.
    """
    return []

@router.get("/{document_id}")
async def get_document_status(document_id: str):
    """
    Get the details and processing status of a specific document.
    """
    return {"document_id": document_id, "status": "processing"}

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its associated knowledge graph.
    """
    return {"message": f"Document {document_id} deleted."}
