"""Search Endpoints - STUB."""
from fastapi import APIRouter

router = APIRouter()

@router.post("")
async def search():
    """Hybrid search - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("/suggestions")
async def search_suggestions():
    """Get search suggestions - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("/expertise")
async def find_expertise():
    """Find expertise - TODO: Implement."""
    return {"status": "not_implemented"}
