"""Document Ingestion Endpoints - STUB."""
from fastapi import APIRouter

router = APIRouter()

@router.post("/ingest")
async def ingest_document():
    """Ingest a document - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("")
async def list_documents():
    """List documents - TODO: Implement."""
    return {"status": "not_implemented"}
