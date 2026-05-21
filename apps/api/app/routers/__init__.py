"""Router modules for G-Brain API."""

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

__all__ = [
    "health",
    "auth",
    "documents",
    "graph",
    "memory",
    "skills",
    "agents",
    "search",
    "governance",
]
