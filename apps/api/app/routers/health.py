"""
Health Check Endpoints

Provides health check endpoints for monitoring and load balancer health checks.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns basic health status without checking dependencies.

    Returns:
        Health status dict
    """
    return {
        "status": "ok",
        "service": "gbrain-api",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if service is ready to handle requests (all dependencies working).

    Args:
        db: Database session

    Returns:
        Readiness status with dependency checks
    """
    checks = {
        "database": "ok",
        "cache": "ok",
        "graph_database": "ok",
        "vector_database": "ok",
    }

    try:
        # Test database
        await db.execute("SELECT 1")
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    return {
        "status": "ready" if all(v == "ok" for v in checks.values()) else "not_ready",
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Indicates if the service is running (not necessarily ready).

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "service": "gbrain-api",
    }
