"""Skills Endpoints - STUB."""
from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def list_skills():
    """List skills - TODO: Implement."""
    return {"status": "not_implemented"}

@router.post("")
async def create_skill():
    """Create skill - TODO: Implement."""
    return {"status": "not_implemented"}

@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get skill - TODO: Implement."""
    return {"status": "not_implemented"}

@router.post("/{skill_id}/execute")
async def execute_skill(skill_id: str):
    """Execute skill - TODO: Implement."""
    return {"status": "not_implemented"}
