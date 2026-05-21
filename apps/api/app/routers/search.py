"""
Search Endpoints

Advanced hybrid search combining semantic, keyword, and graph-based search.
Includes expertise discovery and workflow search.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.search import (
    SearchEngine,
    SearchType,
    ExpertiseFinder,
    WorkflowSearcher,
    SimilarityFinder,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchQuery(BaseModel):
    """Search query."""
    query: str
    search_type: str = "hybrid"
    limit: int = 20


@router.post("")
async def search(
    request: SearchQuery,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Perform hybrid search across knowledge base.

    Combines semantic, keyword, and graph-based search.

    Args:
        request: Search request
        db: Database session

    Returns:
        Search results
    """
    logger.info(f"Search: {request.query} (type={request.search_type})")

    try:
        search_engine = SearchEngine()

        # Map string to enum
        search_type_map = {
            "semantic": SearchType.SEMANTIC,
            "keyword": SearchType.KEYWORD,
            "graph": SearchType.GRAPH,
            "hybrid": SearchType.HYBRID,
        }

        search_type = search_type_map.get(request.search_type, SearchType.HYBRID)

        # Execute search
        response = await search_engine.search(
            query=request.query,
            search_type=search_type,
            limit=request.limit,
        )

        return response.to_dict()

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "query": request.query,
            "results": [],
        }


@router.get("/suggestions")
async def search_suggestions(
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get search suggestions and autocomplete.

    Args:
        query: Partial query
        db: Database session

    Returns:
        Suggestions
    """
    logger.info(f"Search suggestions: {query}")

    try:
        search_engine = SearchEngine()
        response = await search_engine.search_with_suggestions(query)
        return response

    except Exception as e:
        logger.error(f"Suggestions failed: {e}", exc_info=True)
        return {"suggestions": []}


@router.get("/expertise")
async def find_expertise(
    skill: str = Query(..., description="Skill or domain"),
    min_confidence: float = Query(0.7),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Find domain experts for a skill.

    Args:
        skill: Skill or domain
        min_confidence: Minimum confidence
        limit: Maximum results
        db: Database session

    Returns:
        List of experts
    """
    logger.info(f"Finding experts for: {skill}")

    try:
        finder = ExpertiseFinder()
        experts = await finder.find_experts(
            skill=skill,
            min_confidence=min_confidence,
            limit=limit,
        )

        return {
            "skill": skill,
            "experts": experts,
            "total": len(experts),
        }

    except Exception as e:
        logger.error(f"Expertise search failed: {e}", exc_info=True)
        return {
            "skill": skill,
            "experts": [],
            "error": str(e),
        }


@router.get("/workflows")
async def find_workflows(
    query: str = Query(..., description="Workflow search query"),
    category: Optional[str] = Query(None),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Find workflow procedures and SOPs.

    Args:
        query: Search query
        category: Filter by category
        limit: Maximum results
        db: Database session

    Returns:
        List of workflows
    """
    logger.info(f"Finding workflows: {query}")

    try:
        searcher = WorkflowSearcher()
        workflows = await searcher.find_workflows(
            query=query,
            category=category,
            limit=limit,
        )

        return {
            "query": query,
            "workflows": workflows,
            "total": len(workflows),
        }

    except Exception as e:
        logger.error(f"Workflow search failed: {e}", exc_info=True)
        return {
            "query": query,
            "workflows": [],
            "error": str(e),
        }


@router.get("/similar")
async def find_similar(
    item_id: str = Query(..., description="Item ID"),
    item_type: str = Query(..., description="Item type (document, skill, workflow)"),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Find similar items.

    Args:
        item_id: Item to find similarities for
        item_type: Type of item
        limit: Maximum results
        db: Database session

    Returns:
        Similar items
    """
    logger.info(f"Finding similar {item_type}: {item_id}")

    try:
        finder = SimilarityFinder()
        similar = await finder.find_similar(
            item_id=item_id,
            item_type=item_type,
            limit=limit,
        )

        return {
            "item_id": item_id,
            "item_type": item_type,
            "similar": [r.to_dict() for r in similar],
            "total": len(similar),
        }

    except Exception as e:
        logger.error(f"Similarity search failed: {e}", exc_info=True)
        return {
            "item_id": item_id,
            "similar": [],
            "error": str(e),
        }
