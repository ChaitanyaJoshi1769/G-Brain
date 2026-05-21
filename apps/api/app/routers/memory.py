"""Memory System Endpoints - STUB."""
from fastapi import APIRouter

router = APIRouter()

@router.post("/store")
async def store_memory():
    """Store memory - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("/retrieve")
async def retrieve_memory():
    """Retrieve memory - TODO: Implement."""
    return {"status": "not_implemented"}

@router.post("/consolidate")
async def consolidate_memory():
    """Consolidate memory - TODO: Implement."""
    return {"status": "not_implemented"}
