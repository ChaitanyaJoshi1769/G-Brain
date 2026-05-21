"""
Tests for Memory Consolidation Engine
"""

import pytest
from datetime import datetime, timedelta
from app.services.memory_consolidation import (
    MemoryConsolidator,
    FactMerger,
    ConflictResolver,
    RelevanceScorer,
    DecayCalculator,
    Fact,
    ConflictResolution,
)


@pytest.fixture
def sample_facts():
    """Sample facts for testing."""
    base_time = datetime.utcnow()
    return [
        Fact(
            id="fact-1",
            subject="Alice",
            predicate="is_expert_in",
            object="Python",
            confidence=0.95,
            sources=["doc-1", "doc-2"],
            frequency=3,
            last_accessed=base_time,
            created_at=base_time - timedelta(days=10),
        ),
        Fact(
            id="fact-2",
            subject="Alice",
            predicate="is_expert_in",
            object="Python",
            confidence=0.92,
            sources=["doc-3"],
            frequency=2,
            last_accessed=base_time,
            created_at=base_time - timedelta(days=5),
        ),
        Fact(
            id="fact-3",
            subject="Bob",
            predicate="is_expert_in",
            object="Java",
            confidence=0.88,
            sources=["doc-4"],
            frequency=1,
            last_accessed=base_time - timedelta(days=20),
            created_at=base_time - timedelta(days=30),
        ),
        Fact(
            id="fact-4",
            subject="Charlie",
            predicate="is_expert_in",
            object="JavaScript",
            confidence=0.85,
            sources=["doc-5"],
            frequency=2,
            last_accessed=base_time,
            created_at=base_time - timedelta(days=3),
        ),
        Fact(
            id="fact-5",
            subject="Alice",
            predicate="has_certification",
            object="AWS",
            confidence=0.9,
            sources=["doc-6"],
            frequency=1,
            last_accessed=base_time,
            created_at=base_time - timedelta(days=15),
        ),
    ]


@pytest.fixture
def conflicting_facts():
    """Sample facts with conflicts."""
    base_time = datetime.utcnow()
    return [
        Fact(
            id="conflict-1a",
            subject="TeamA",
            predicate="responsibility_area",
            object="Backend",
            confidence=0.9,
            sources=["doc-org-1"],
            created_at=base_time - timedelta(days=30),
        ),
        Fact(
            id="conflict-1b",
            subject="TeamA",
            predicate="responsibility_area",
            object="Frontend",
            confidence=0.8,
            sources=["doc-org-2"],
            created_at=base_time - timedelta(days=20),
        ),
        Fact(
            id="conflict-2a",
            subject="Project X",
            predicate="status",
            object="Completed",
            confidence=0.95,
            sources=["doc-status-1"],
            created_at=base_time - timedelta(days=5),
        ),
        Fact(
            id="conflict-2b",
            subject="Project X",
            predicate="status",
            object="In Progress",
            confidence=0.7,
            sources=["doc-status-2"],
            created_at=base_time - timedelta(days=1),
        ),
    ]


class TestFactMerger:
    @pytest.mark.asyncio
    async def test_merge_facts(self, sample_facts):
        """Test fact merging."""
        merger = FactMerger()

        merged = await merger.merge_facts(sample_facts, similarity_threshold=0.8)

        assert isinstance(merged, list)
        # Should have fewer facts after merging similar ones
        assert len(merged) <= len(sample_facts)

    @pytest.mark.asyncio
    async def test_merge_facts_high_threshold(self, sample_facts):
        """Test fact merging with high threshold."""
        merger = FactMerger()

        # High threshold = fewer merges
        merged_high = await merger.merge_facts(sample_facts, similarity_threshold=0.95)
        # Low threshold = more merges
        merged_low = await merger.merge_facts(sample_facts, similarity_threshold=0.5)

        assert len(merged_low) <= len(merged_high)

    def test_calculate_similarity(self, sample_facts):
        """Test similarity calculation."""
        merger = FactMerger()

        # Same facts should have high similarity
        similarity = merger._calculate_similarity(sample_facts[0], sample_facts[1])
        assert 0 <= similarity <= 1
        # Facts 0 and 1 are very similar
        assert similarity > 0.8

        # Different facts should have lower similarity
        similarity2 = merger._calculate_similarity(sample_facts[0], sample_facts[2])
        assert similarity2 < similarity

    def test_merge_fact_group(self, sample_facts):
        """Test merging a group of facts."""
        merger = FactMerger()

        # Merge first two facts (about Alice and Python)
        merged = merger._merge_fact_group([sample_facts[0], sample_facts[1]])

        assert merged.subject == sample_facts[0].subject
        assert merged.predicate == sample_facts[0].predicate
        assert merged.confidence <= 1.0
        assert len(merged.sources) > len(sample_facts[0].sources)
        assert merged.frequency == 5  # 3 + 2


class TestConflictResolver:
    @pytest.mark.asyncio
    async def test_resolve_conflicts(self, conflicting_facts):
        """Test conflict resolution."""
        resolver = ConflictResolver()

        resolved, conflicts = await resolver.resolve_conflicts(conflicting_facts)

        assert isinstance(resolved, list)
        assert isinstance(conflicts, list)
        # Should have identified some conflicts
        assert len(conflicts) > 0

    def test_are_contradictory(self, conflicting_facts):
        """Test contradiction detection."""
        resolver = ConflictResolver()

        # conflict-1a and conflict-1b are contradictory
        is_contradictory = resolver._are_contradictory(
            conflicting_facts[0], conflicting_facts[1]
        )
        assert is_contradictory is True

        # Non-contradictory facts
        is_contradictory2 = resolver._are_contradictory(
            conflicting_facts[0], conflicting_facts[2]
        )
        assert is_contradictory2 is False

    def test_resolve_conflict(self, conflicting_facts):
        """Test conflict resolution strategy."""
        resolver = ConflictResolver()

        resolution = resolver._resolve_conflict(
            conflicting_facts[0], conflicting_facts[1]
        )

        assert isinstance(resolution, ConflictResolution)
        assert resolution.resolution in [
            "merge",
            "keep_first",
            "keep_second",
            "flag_conflict",
        ]
        assert 0 <= resolution.confidence <= 1
        assert resolution.reasoning is not None

    def test_merge_conflicting(self, conflicting_facts):
        """Test merging conflicting facts."""
        resolver = ConflictResolver()

        merged = resolver._merge_conflicting(conflicting_facts[0], conflicting_facts[1])

        assert merged.subject == conflicting_facts[0].subject
        assert merged.predicate == conflicting_facts[0].predicate
        # Object should indicate both options
        assert "or" in merged.object


class TestRelevanceScorer:
    @pytest.mark.asyncio
    async def test_score_relevance(self, sample_facts):
        """Test relevance scoring."""
        scorer = RelevanceScorer()

        scores = await scorer.score_relevance(sample_facts)

        assert isinstance(scores, dict)
        assert len(scores) == len(sample_facts)
        for fact_id, score in scores.items():
            assert 0 <= score <= 1

    @pytest.mark.asyncio
    async def test_score_relevance_weights(self, sample_facts):
        """Test relevance scoring with different weights."""
        scorer = RelevanceScorer()

        # Recency-focused
        scores_recency = await scorer.score_relevance(
            sample_facts, recency_weight=0.7, frequency_weight=0.15, confidence_weight=0.15
        )

        # Confidence-focused
        scores_confidence = await scorer.score_relevance(
            sample_facts, recency_weight=0.15, frequency_weight=0.15, confidence_weight=0.7
        )

        assert isinstance(scores_recency, dict)
        assert isinstance(scores_confidence, dict)

    @pytest.mark.asyncio
    async def test_filter_by_relevance(self, sample_facts):
        """Test relevance-based filtering."""
        scorer = RelevanceScorer()

        filtered = await scorer.filter_by_relevance(sample_facts, min_relevance=0.5)

        assert isinstance(filtered, list)
        assert len(filtered) <= len(sample_facts)

        # All filtered facts should meet threshold
        scores = await scorer.score_relevance(filtered)
        for fact_id in scores:
            assert scores[fact_id] >= 0.5


class TestDecayCalculator:
    @pytest.mark.asyncio
    async def test_calculate_decay(self, sample_facts):
        """Test decay calculation."""
        calculator = DecayCalculator()

        decayed = await calculator.calculate_decay(sample_facts, base_decay_rate=0.01)

        assert isinstance(decayed, list)
        assert len(decayed) == len(sample_facts)

        # Old facts should have lower confidence
        for i, (original, decayed_fact) in enumerate(zip(sample_facts, decayed)):
            if i != 0:  # First fact might already be at min_confidence
                assert decayed_fact.confidence <= original.confidence

    @pytest.mark.asyncio
    async def test_calculate_decay_rates(self, sample_facts):
        """Test different decay rates."""
        calculator = DecayCalculator()

        # High decay rate
        decayed_high = await calculator.calculate_decay(sample_facts, base_decay_rate=0.05)
        # Low decay rate
        decayed_low = await calculator.calculate_decay(sample_facts, base_decay_rate=0.01)

        # Higher decay rate should result in lower confidence
        for fact_high, fact_low in zip(decayed_high, decayed_low):
            assert fact_high.confidence <= fact_low.confidence

    @pytest.mark.asyncio
    async def test_refresh_fact(self, sample_facts):
        """Test fact refresh."""
        calculator = DecayCalculator()

        original = sample_facts[0]
        refreshed = await calculator.refresh_fact(original)

        # Refreshed fact should have higher confidence (boosted by 5%)
        assert refreshed.confidence > original.confidence
        assert refreshed.frequency > original.frequency
        assert refreshed.last_accessed > original.last_accessed


class TestMemoryConsolidator:
    @pytest.mark.asyncio
    async def test_consolidate_memory(self, sample_facts):
        """Test full memory consolidation."""
        consolidator = MemoryConsolidator()

        result = await consolidator.consolidate_memory(
            sample_facts, apply_decay=True, min_relevance=0.3
        )

        assert isinstance(result, dict)
        assert "original_count" in result
        assert "final_count" in result
        assert "merged_count" in result
        assert "conflicts_found" in result
        assert "duplicates_removed" in result
        assert "consolidation_ratio" in result
        assert "facts" in result
        assert "fact_scores" in result

        # Stats should be consistent
        assert result["original_count"] >= result["final_count"]
        assert result["final_count"] <= result["merged_count"]

    @pytest.mark.asyncio
    async def test_consolidate_memory_with_conflicts(self, conflicting_facts):
        """Test consolidation with conflicting facts."""
        consolidator = MemoryConsolidator()

        result = await consolidator.consolidate_memory(
            conflicting_facts, apply_decay=False
        )

        assert isinstance(result, dict)
        assert result["conflicts_found"] > 0
        assert "conflicts" in result

    @pytest.mark.asyncio
    async def test_consolidate_memory_decay_disabled(self, sample_facts):
        """Test consolidation without decay."""
        consolidator = MemoryConsolidator()

        result = await consolidator.consolidate_memory(
            sample_facts, apply_decay=False
        )

        assert isinstance(result, dict)
        # Without decay, confidences should remain similar
        assert "facts" in result

    @pytest.mark.asyncio
    async def test_learn_from_facts(self, sample_facts):
        """Test learning patterns from facts."""
        consolidator = MemoryConsolidator()

        patterns = await consolidator.learn_from_facts(sample_facts)

        assert isinstance(patterns, dict)
        assert "total_facts" in patterns
        assert "unique_subjects" in patterns
        assert "unique_predicates" in patterns
        assert "unique_objects" in patterns
        assert "most_common_relationships" in patterns
        assert "most_confident_facts" in patterns
        assert "most_mentioned_subjects" in patterns
        assert "most_mentioned_objects" in patterns
        assert "average_confidence" in patterns

        assert patterns["total_facts"] == len(sample_facts)
        assert 0 <= patterns["average_confidence"] <= 1


class TestFact:
    def test_fact_creation(self):
        """Test fact creation."""
        fact = Fact(
            id="test-fact",
            subject="Entity",
            predicate="relationship",
            object="Target",
            confidence=0.9,
            sources=["doc-1"],
        )

        assert fact.id == "test-fact"
        assert fact.subject == "Entity"
        assert fact.confidence == 0.9

    def test_fact_to_dict(self):
        """Test fact serialization."""
        fact = Fact(
            id="test-fact",
            subject="Entity",
            predicate="relationship",
            object="Target",
            confidence=0.9,
        )

        result = fact.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test-fact"
        assert result["subject"] == "Entity"
        assert result["confidence"] == 0.9


class TestConflictResolution:
    def test_conflict_resolution_creation(self, sample_facts):
        """Test conflict resolution creation."""
        resolution = ConflictResolution(
            fact1=sample_facts[0],
            fact2=sample_facts[1],
            resolution="merge",
            confidence=0.9,
            reasoning="High similarity",
        )

        assert resolution.resolution == "merge"
        assert resolution.confidence == 0.9


@pytest.mark.asyncio
async def test_end_to_end_consolidation(sample_facts):
    """Test end-to-end memory consolidation."""
    consolidator = MemoryConsolidator()

    # Run full pipeline
    consolidation_result = await consolidator.consolidate_memory(
        sample_facts, apply_decay=True, min_relevance=0.3
    )

    assert consolidation_result["final_count"] > 0
    assert len(consolidation_result["facts"]) > 0

    # Learn from consolidated facts
    patterns = await consolidator.learn_from_facts(consolidation_result["facts"])

    assert patterns["total_facts"] > 0
    assert patterns["average_confidence"] > 0


@pytest.mark.asyncio
async def test_consolidation_with_decay_and_relevance(sample_facts):
    """Test consolidation with decay and relevance filtering."""
    consolidator = MemoryConsolidator()

    result = await consolidator.consolidate_memory(
        sample_facts, apply_decay=True, min_relevance=0.5
    )

    # More stringent filtering should result in fewer facts
    result_lenient = await consolidator.consolidate_memory(
        sample_facts, apply_decay=True, min_relevance=0.1
    )

    assert result["final_count"] <= result_lenient["final_count"]
