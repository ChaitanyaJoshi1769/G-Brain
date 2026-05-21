"""
Tests for Advanced Search Engine
"""

import pytest
from app.services.search import (
    SearchEngine,
    SearchType,
    SearchResult,
    SearchResponse,
    SemanticSearcher,
    KeywordSearcher,
    GraphSearcher,
    HybridSearcher,
    ExpertiseFinder,
    WorkflowSearcher,
    SimilarityFinder,
)


@pytest.fixture
def sample_search_results():
    """Sample search results."""
    return [
        SearchResult(
            id="doc-1",
            type="document",
            title="Refund Processing Workflow",
            excerpt="This document outlines the refund processing workflow...",
            relevance_score=0.95,
            source="documents",
            metadata={"category": "operations"},
        ),
        SearchResult(
            id="doc-2",
            type="document",
            title="Payment Processing Guide",
            excerpt="Guide for processing customer payments...",
            relevance_score=0.87,
            source="documents",
            metadata={"category": "finance"},
        ),
        SearchResult(
            id="skill-1",
            type="skill",
            title="Process Refund Skill",
            excerpt="Automated skill for processing refunds...",
            relevance_score=0.92,
            source="skills",
        ),
        SearchResult(
            id="person-1",
            type="person",
            title="Alice Johnson",
            excerpt="Expert in refund processing with 5 years experience...",
            relevance_score=0.85,
            source="graph",
            metadata={"expertise": ["refunds", "payments"]},
        ),
    ]


@pytest.fixture
def sample_workflow_results():
    """Sample workflow search results."""
    return [
        {
            "id": "workflow-1",
            "name": "Customer Refund Workflow",
            "steps": 7,
            "category": "customer_service",
            "success_rate": 0.94,
            "average_duration_minutes": 53,
            "last_executed": "2 hours ago",
        },
        {
            "id": "workflow-2",
            "name": "Payment Processing Workflow",
            "steps": 5,
            "category": "finance",
            "success_rate": 0.98,
            "average_duration_minutes": 15,
            "last_executed": "30 minutes ago",
        },
        {
            "id": "workflow-3",
            "name": "Approval Request Workflow",
            "steps": 4,
            "category": "management",
            "success_rate": 0.91,
            "average_duration_minutes": 120,
            "last_executed": "1 day ago",
        },
    ]


@pytest.fixture
def sample_experts():
    """Sample expert results."""
    return [
        {
            "id": "expert-1",
            "name": "Alice Johnson",
            "email": "alice@company.com",
            "expertise_level": "high",
            "confidence": 0.95,
            "projects": 12,
            "availability": "high",
        },
        {
            "id": "expert-2",
            "name": "Bob Smith",
            "email": "bob@company.com",
            "expertise_level": "medium",
            "confidence": 0.78,
            "projects": 8,
            "availability": "medium",
        },
        {
            "id": "expert-3",
            "name": "Charlie Davis",
            "email": "charlie@company.com",
            "expertise_level": "high",
            "confidence": 0.88,
            "projects": 15,
            "availability": "low",
        },
    ]


class TestSearchResult:
    def test_search_result_creation(self):
        """Test search result creation."""
        result = SearchResult(
            id="doc-1",
            type="document",
            title="Test Document",
            excerpt="Test excerpt...",
            relevance_score=0.9,
            source="documents",
        )

        assert result.id == "doc-1"
        assert result.type == "document"
        assert result.relevance_score == 0.9

    def test_search_result_to_dict(self):
        """Test search result serialization."""
        result = SearchResult(
            id="doc-1",
            type="document",
            title="Test Document",
            excerpt="Test excerpt...",
            relevance_score=0.9,
            source="documents",
            metadata={"category": "test"},
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["id"] == "doc-1"
        assert result_dict["relevance_score"] == 0.9
        assert "metadata" in result_dict


class TestSearchResponse:
    def test_search_response_creation(self, sample_search_results):
        """Test search response creation."""
        response = SearchResponse(
            query="refund",
            search_type=SearchType.HYBRID,
            total_results=len(sample_search_results),
            results=sample_search_results,
            execution_time_ms=125.5,
        )

        assert response.query == "refund"
        assert response.search_type == SearchType.HYBRID
        assert response.total_results == len(sample_search_results)

    def test_search_response_to_dict(self, sample_search_results):
        """Test search response serialization."""
        response = SearchResponse(
            query="refund",
            search_type=SearchType.HYBRID,
            total_results=len(sample_search_results),
            results=sample_search_results,
            execution_time_ms=125.5,
            facets={"type": [("document", 2), ("skill", 1), ("person", 1)]},
        )

        response_dict = response.to_dict()

        assert isinstance(response_dict, dict)
        assert response_dict["query"] == "refund"
        assert response_dict["search_type"] == "hybrid"
        assert len(response_dict["results"]) > 0


class TestSemanticSearcher:
    @pytest.mark.asyncio
    async def test_semantic_search(self):
        """Test semantic search."""
        searcher = SemanticSearcher()

        results = await searcher.search(query="refund processing", limit=10)

        assert isinstance(results, list)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.source == "documents"

    @pytest.mark.asyncio
    async def test_semantic_search_limit(self):
        """Test semantic search with limit."""
        searcher = SemanticSearcher()

        results_5 = await searcher.search(query="refund", limit=5)
        results_10 = await searcher.search(query="refund", limit=10)

        assert len(results_5) <= 5
        assert len(results_10) <= 10

    @pytest.mark.asyncio
    async def test_semantic_search_with_threshold(self):
        """Test semantic search with similarity threshold."""
        searcher = SemanticSearcher()

        results_high = await searcher.search(
            query="refund", limit=10, min_similarity=0.8
        )
        results_low = await searcher.search(
            query="refund", limit=10, min_similarity=0.5
        )

        # Higher threshold should give same or fewer results
        assert len(results_high) <= len(results_low)


class TestKeywordSearcher:
    @pytest.mark.asyncio
    async def test_keyword_search(self):
        """Test keyword search."""
        searcher = KeywordSearcher()

        results = await searcher.search(query="refund", limit=10)

        assert isinstance(results, list)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_keyword_search_case_sensitivity(self):
        """Test case sensitivity."""
        searcher = KeywordSearcher()

        results_sensitive = await searcher.search(
            query="Refund", limit=10, case_sensitive=True
        )
        results_insensitive = await searcher.search(
            query="Refund", limit=10, case_sensitive=False
        )

        assert isinstance(results_sensitive, list)
        assert isinstance(results_insensitive, list)


class TestGraphSearcher:
    @pytest.mark.asyncio
    async def test_graph_search(self):
        """Test graph-based search."""
        searcher = GraphSearcher()

        results = await searcher.search(query="refund", limit=10)

        assert isinstance(results, list)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.type == "entity"

    @pytest.mark.asyncio
    async def test_graph_search_max_depth(self):
        """Test graph search with depth limit."""
        searcher = GraphSearcher()

        results_shallow = await searcher.search(
            query="refund", limit=10, max_depth=1
        )
        results_deep = await searcher.search(query="refund", limit=10, max_depth=3)

        assert isinstance(results_shallow, list)
        assert isinstance(results_deep, list)


class TestHybridSearcher:
    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid search."""
        searcher = HybridSearcher()

        response = await searcher.search(query="refund", limit=20)

        assert isinstance(response, SearchResponse)
        assert response.query == "refund"
        assert response.search_type == SearchType.HYBRID
        assert len(response.results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_search_with_weights(self):
        """Test hybrid search with custom weights."""
        searcher = HybridSearcher()

        weights_semantic = {"semantic": 0.6, "keyword": 0.2, "graph": 0.2}
        response = await searcher.search(
            query="refund", limit=20, weights=weights_semantic
        )

        assert isinstance(response, SearchResponse)
        assert len(response.results) > 0

    def test_calculate_facets(self, sample_search_results):
        """Test facet calculation."""
        searcher = HybridSearcher()

        facets = searcher._calculate_facets(sample_search_results)

        assert isinstance(facets, dict)
        assert "type" in facets
        assert "source" in facets
        # Type facet should list types and their counts
        assert len(facets["type"]) > 0


class TestExpertiseFinder:
    @pytest.mark.asyncio
    async def test_find_experts(self):
        """Test expert finding."""
        finder = ExpertiseFinder()

        experts = await finder.find_experts(skill="Python", limit=10)

        assert isinstance(experts, list)
        assert len(experts) > 0
        for expert in experts:
            assert isinstance(expert, dict)
            assert "name" in expert
            assert "confidence" in expert

    @pytest.mark.asyncio
    async def test_find_experts_min_confidence(self):
        """Test expert finding with confidence threshold."""
        finder = ExpertiseFinder()

        experts_high = await finder.find_experts(
            skill="Python", min_confidence=0.8, limit=10
        )
        experts_low = await finder.find_experts(
            skill="Python", min_confidence=0.5, limit=10
        )

        # Higher threshold should give same or fewer experts
        assert len(experts_high) <= len(experts_low)

    @pytest.mark.asyncio
    async def test_find_experts_limit(self):
        """Test expert finding with limit."""
        finder = ExpertiseFinder()

        experts_3 = await finder.find_experts(skill="Python", limit=3)
        experts_10 = await finder.find_experts(skill="Python", limit=10)

        assert len(experts_3) <= 3
        assert len(experts_10) <= 10


class TestWorkflowSearcher:
    @pytest.mark.asyncio
    async def test_find_workflows(self):
        """Test workflow finding."""
        searcher = WorkflowSearcher()

        workflows = await searcher.find_workflows(query="refund", limit=10)

        assert isinstance(workflows, list)
        assert len(workflows) > 0
        for workflow in workflows:
            assert isinstance(workflow, dict)
            assert "name" in workflow
            assert "steps" in workflow

    @pytest.mark.asyncio
    async def test_find_workflows_by_category(self):
        """Test workflow finding by category."""
        searcher = WorkflowSearcher()

        workflows = await searcher.find_workflows(
            query="refund", category="operations", limit=10
        )

        assert isinstance(workflows, list)

    @pytest.mark.asyncio
    async def test_find_workflows_limit(self):
        """Test workflow finding with limit."""
        searcher = WorkflowSearcher()

        workflows_5 = await searcher.find_workflows(query="refund", limit=5)
        workflows_20 = await searcher.find_workflows(query="refund", limit=20)

        assert len(workflows_5) <= 5
        assert len(workflows_20) <= 20


class TestSimilarityFinder:
    @pytest.mark.asyncio
    async def test_find_similar(self):
        """Test similarity finding."""
        finder = SimilarityFinder()

        similar = await finder.find_similar(
            item_id="doc-1", item_type="document", limit=10
        )

        assert isinstance(similar, list)
        assert len(similar) > 0
        for result in similar:
            assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_find_similar_different_types(self):
        """Test similarity finding for different item types."""
        finder = SimilarityFinder()

        for item_type in ["document", "skill", "workflow"]:
            similar = await finder.find_similar(
                item_id="item-1", item_type=item_type, limit=5
            )
            assert isinstance(similar, list)
            assert all(r.type == item_type for r in similar)

    @pytest.mark.asyncio
    async def test_find_similar_min_similarity(self):
        """Test similarity finding with threshold."""
        finder = SimilarityFinder()

        similar_high = await finder.find_similar(
            item_id="doc-1", item_type="document", limit=10, min_similarity=0.8
        )
        similar_low = await finder.find_similar(
            item_id="doc-1", item_type="document", limit=10, min_similarity=0.5
        )

        assert isinstance(similar_high, list)
        assert isinstance(similar_low, list)


class TestSearchEngine:
    @pytest.mark.asyncio
    async def test_search_hybrid(self):
        """Test hybrid search via search engine."""
        engine = SearchEngine()

        response = await engine.search(query="refund", search_type=SearchType.HYBRID)

        assert isinstance(response, SearchResponse)
        assert response.search_type == SearchType.HYBRID
        assert len(response.results) > 0

    @pytest.mark.asyncio
    async def test_search_semantic(self):
        """Test semantic search via search engine."""
        engine = SearchEngine()

        response = await engine.search(query="refund", search_type=SearchType.SEMANTIC)

        assert isinstance(response, SearchResponse)
        assert response.search_type == SearchType.SEMANTIC

    @pytest.mark.asyncio
    async def test_search_keyword(self):
        """Test keyword search via search engine."""
        engine = SearchEngine()

        response = await engine.search(query="refund", search_type=SearchType.KEYWORD)

        assert isinstance(response, SearchResponse)
        assert response.search_type == SearchType.KEYWORD

    @pytest.mark.asyncio
    async def test_search_graph(self):
        """Test graph search via search engine."""
        engine = SearchEngine()

        response = await engine.search(query="refund", search_type=SearchType.GRAPH)

        assert isinstance(response, SearchResponse)
        assert response.search_type == SearchType.GRAPH

    @pytest.mark.asyncio
    async def test_search_with_suggestions(self):
        """Test search with suggestions."""
        engine = SearchEngine()

        result = await engine.search_with_suggestions(query="ref")

        assert isinstance(result, dict)
        assert "query" in result
        assert "results" in result
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    @pytest.mark.asyncio
    async def test_search_limit(self):
        """Test search with limit."""
        engine = SearchEngine()

        response_10 = await engine.search(query="refund", limit=10)
        response_30 = await engine.search(query="refund", limit=30)

        assert len(response_10.results) <= 10
        assert len(response_30.results) <= 30


@pytest.mark.asyncio
async def test_end_to_end_search(sample_search_results):
    """Test end-to-end search workflow."""
    engine = SearchEngine()

    # Perform hybrid search
    response = await engine.search(query="refund processing", search_type=SearchType.HYBRID)

    assert isinstance(response, SearchResponse)
    assert len(response.results) > 0
    assert response.query == "refund processing"

    # Get suggestions
    suggestions = await engine.search_with_suggestions(query="ref")

    assert "suggestions" in suggestions
    assert isinstance(suggestions["suggestions"], list)


@pytest.mark.asyncio
async def test_multi_strategy_search():
    """Test searching with multiple strategies."""
    engine = SearchEngine()

    # Run all search types
    hybrid = await engine.search(query="refund", search_type=SearchType.HYBRID)
    semantic = await engine.search(query="refund", search_type=SearchType.SEMANTIC)
    keyword = await engine.search(query="refund", search_type=SearchType.KEYWORD)
    graph = await engine.search(query="refund", search_type=SearchType.GRAPH)

    assert isinstance(hybrid, SearchResponse)
    assert isinstance(semantic, SearchResponse)
    assert isinstance(keyword, SearchResponse)
    assert isinstance(graph, SearchResponse)

    # Each should return results
    assert len(hybrid.results) > 0
    assert len(semantic.results) > 0
    assert len(keyword.results) > 0
    assert len(graph.results) > 0


@pytest.mark.asyncio
async def test_expertise_and_workflow_discovery():
    """Test expertise and workflow discovery together."""
    expertise_finder = ExpertiseFinder()
    workflow_searcher = WorkflowSearcher()

    # Find experts and workflows for a skill
    experts = await expertise_finder.find_experts(skill="refund processing")
    workflows = await workflow_searcher.find_workflows(query="refund processing")

    assert len(experts) > 0
    assert len(workflows) > 0

    # Each expert should have expertise info
    for expert in experts:
        assert "name" in expert
        assert "confidence" in expert

    # Each workflow should have execution metrics
    for workflow in workflows:
        assert "steps" in workflow
        assert "success_rate" in workflow
