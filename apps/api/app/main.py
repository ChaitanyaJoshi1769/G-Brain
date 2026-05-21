"""
G-Brain API Server - Main Application
Production-grade FastAPI application with complete middleware, exception handling,
monitoring, and API endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, get_db_session, init_db
from app.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
)
from app.observability import setup_tracing, setup_metrics
from app.routers import (
    health,
    auth,
    documents,
    graph,
    memory,
    skills,
    agents,
    search,
    governance,
)
from app.exception_handlers import setup_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting G-Brain API Server...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"API Version: {settings.API_VERSION}")

    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()

        # Setup observability
        if settings.ENABLE_TRACING:
            logger.info("Setting up distributed tracing...")
            setup_tracing(app)

        if settings.ENABLE_METRICS:
            logger.info("Setting up metrics collection...")
            setup_metrics(app)

        logger.info("G-Brain API Server ready!")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down G-Brain API Server...")
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="G-Brain API",
        description="Enterprise AI Intelligence Operating System",
        version=settings.API_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # =========================================================================
    # MIDDLEWARE
    # =========================================================================

    # Trust headers from reverse proxy
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "*.example.com",
            settings.API_HOST,
        ],
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
    )

    # Gzip compression
    app.add_middleware(GZIPMiddleware, minimum_size=1000)

    # Custom middleware (order matters - innermost first)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # =========================================================================
    # EXCEPTION HANDLERS
    # =========================================================================

    setup_exception_handlers(app)

    # =========================================================================
    # ROUTES
    # =========================================================================

    # Health check
    app.include_router(health.router, tags=["Health"])

    # Authentication
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

    # Document Ingestion
    app.include_router(
        documents.router,
        prefix="/api/v1/documents",
        tags=["Documents"],
    )

    # Knowledge Graph
    app.include_router(
        graph.router,
        prefix="/api/v1/graph",
        tags=["Knowledge Graph"],
    )

    # Memory System
    app.include_router(
        memory.router,
        prefix="/api/v1/memory",
        tags=["Memory"],
    )

    # Skills
    app.include_router(
        skills.router,
        prefix="/api/v1/skills",
        tags=["Skills"],
    )

    # Agents
    app.include_router(
        agents.router,
        prefix="/api/v1/agents",
        tags=["Agents"],
    )

    # Search
    app.include_router(
        search.router,
        prefix="/api/v1/search",
        tags=["Search"],
    )

    # Governance
    app.include_router(
        governance.router,
        prefix="/api/v1/governance",
        tags=["Governance"],
    )

    # =========================================================================
    # DOCUMENTATION
    # =========================================================================

    def custom_openapi():
        """Customize OpenAPI schema."""
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="G-Brain API",
            version=settings.API_VERSION,
            description="Enterprise AI Intelligence Operating System API",
            routes=app.routes,
            tags=[
                {
                    "name": "Health",
                    "description": "Health check and status endpoints",
                },
                {
                    "name": "Authentication",
                    "description": "User authentication and authorization",
                },
                {
                    "name": "Documents",
                    "description": "Document ingestion and management",
                },
                {
                    "name": "Knowledge Graph",
                    "description": "Organizational knowledge graph queries",
                },
                {
                    "name": "Memory",
                    "description": "Company memory storage and retrieval",
                },
                {
                    "name": "Skills",
                    "description": "AI skill definitions and execution",
                },
                {
                    "name": "Agents",
                    "description": "AI agent management and execution",
                },
                {
                    "name": "Search",
                    "description": "Hybrid search across knowledge base",
                },
                {
                    "name": "Governance",
                    "description": "Approvals, policies, and audit logs",
                },
            ],
        )

        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerToken": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from /api/v1/auth/token",
            }
        }

        # Add authentication to all routes except public ones
        for path, path_item in openapi_schema["paths"].items():
            if path not in ["/health", "/healthz", "/api/v1/auth/token"]:
                for method in path_item.values():
                    if isinstance(method, dict) and "responses" in method:
                        method.setdefault("security", [{"BearerToken": []}])

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    if settings.DEBUG:
        app.openapi = custom_openapi  # type: ignore

    # =========================================================================
    # ROOT ENDPOINTS
    # =========================================================================

    @app.get("/", tags=["Info"])
    async def root():
        """Get API information."""
        return {
            "name": "G-Brain API",
            "version": settings.API_VERSION,
            "status": "operational",
            "documentation": "/docs",
            "graphql": "/graphql",
        }

    @app.get("/api/v1", tags=["Info"])
    async def api_root():
        """Get API v1 information."""
        return {
            "version": "1.0.0",
            "endpoints": {
                "docs": "/docs",
                "openapi": "/openapi.json",
                "health": "/health",
                "auth": "/api/v1/auth",
                "documents": "/api/v1/documents",
                "graph": "/api/v1/graph",
                "memory": "/api/v1/memory",
                "skills": "/api/v1/skills",
                "agents": "/api/v1/agents",
                "search": "/api/v1/search",
                "governance": "/api/v1/governance",
            },
        }

    @app.get("/healthz", tags=["Health"])
    async def healthz():
        """Kubernetes-style health check."""
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "version": settings.API_VERSION},
        )

    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=settings.API_WORKERS if not settings.DEBUG else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )
