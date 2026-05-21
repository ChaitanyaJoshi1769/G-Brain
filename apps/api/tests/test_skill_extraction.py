"""
Tests for Skill Extraction Engine
"""

import pytest
from app.services.skill_extraction import (
    SkillExtractor,
    PatternDetector,
    DecisionTreeExtractor,
    HeuristicLearner,
    SkillGenerator,
    SkillType,
)


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "id": "doc-1",
            "content": """
            Refund Process:
            Step 1: Receive refund request
            Then: Validate customer status
            If customer is active: Approve refund
            If customer is inactive: Escalate to manager
            Then: Process payment
            Then: Send confirmation email
            """,
            "created_at": "2024-01-01",
        },
        {
            "id": "doc-2",
            "content": """
            Ticket Escalation:
            If issue is critical: Escalate to senior team
            If issue is high priority: Notify manager
            Then: Create ticket
            Then: Send notification
            """,
            "created_at": "2024-01-02",
        },
        {
            "id": "doc-3",
            "content": """
            Approval Workflow:
            Refund approval required from Finance team if amount > $1000
            Amount $1000-$5000 requires Finance approval
            Amount > $5000 requires Director approval
            """,
            "created_at": "2024-01-03",
        },
    ]


class TestPatternDetector:
    @pytest.mark.asyncio
    async def test_detect_patterns(self, sample_documents):
        """Test pattern detection."""
        detector = PatternDetector()

        result = await detector.detect_patterns(sample_documents, min_frequency=1)

        assert "patterns" in result
        assert len(result["patterns"]) > 0
        assert result["confidence"] >= 0
        assert result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_extract_sequences(self, sample_documents):
        """Test sequence extraction."""
        detector = PatternDetector()

        sequences = detector._extract_sequences(sample_documents)

        assert len(sequences) > 0
        for seq in sequences:
            assert isinstance(seq, list)
            assert all(isinstance(a, str) for a in seq)


class TestDecisionTreeExtractor:
    @pytest.mark.asyncio
    async def test_extract_decision_points(self, sample_documents):
        """Test decision point extraction."""
        extractor = DecisionTreeExtractor()

        decision_points = await extractor.extract_decision_trees(sample_documents)

        assert isinstance(decision_points, list)
        if decision_points:
            dp = decision_points[0]
            assert hasattr(dp, "question")
            assert hasattr(dp, "branches")
            assert isinstance(dp.branches, dict)
            assert dp.confidence >= 0
            assert dp.confidence <= 1


class TestHeuristicLearner:
    @pytest.mark.asyncio
    async def test_learn_heuristics(self, sample_documents):
        """Test heuristic learning."""
        learner = HeuristicLearner()

        heuristics = await learner.learn_heuristics(sample_documents, {})

        assert isinstance(heuristics, list)
        if heuristics:
            h = heuristics[0]
            assert "type" in h
            assert h["type"] in ["approval", "escalation", "exception_handler"]

    @pytest.mark.asyncio
    async def test_extract_approval_rules(self, sample_documents):
        """Test approval rule extraction."""
        learner = HeuristicLearner()

        rules = learner._extract_approval_rules(sample_documents)

        assert isinstance(rules, list)
        for rule in rules:
            assert rule["type"] == "approval"
            assert "role" in rule
            assert "condition" in rule


class TestSkillGenerator:
    @pytest.mark.asyncio
    async def test_generate_skills(self, sample_documents):
        """Test skill generation."""
        detector = PatternDetector()
        extractor = DecisionTreeExtractor()
        learner = HeuristicLearner()
        generator = SkillGenerator()

        # Extract components
        patterns = await detector.detect_patterns(sample_documents)
        decision_points = await extractor.extract_decision_trees(sample_documents)
        heuristics = await learner.learn_heuristics(sample_documents, patterns)

        # Generate skills
        skills = await generator.generate_skills(
            patterns, decision_points, heuristics, category="operations"
        )

        assert isinstance(skills, list)
        if skills:
            skill = skills[0]
            assert hasattr(skill, "name")
            assert hasattr(skill, "skill_type")
            assert hasattr(skill, "extraction_confidence")

    def test_create_workflow_skill(self, sample_documents):
        """Test workflow skill creation."""
        generator = SkillGenerator()

        pattern = {
            "pattern": "receive -> validate -> approve",
            "steps": ["receive", "validate", "approve"],
            "frequency": 5,
            "confidence": 0.9,
        }

        skill = generator._create_workflow_skill(pattern, "operations")

        assert skill.name is not None
        assert skill.skill_type == SkillType.WORKFLOW
        assert len(skill.steps) == 3
        assert skill.is_executable


class TestSkillExtractor:
    @pytest.mark.asyncio
    async def test_extract_skills(self, sample_documents):
        """Test full skill extraction pipeline."""
        extractor = SkillExtractor()

        skills = await extractor.extract_skills(
            documents=sample_documents,
            category="operations",
            min_confidence=0.0,  # Accept all for testing
        )

        assert isinstance(skills, list)
        # Should extract at least some skills
        assert len(skills) > 0

        # Check skill properties
        for skill in skills:
            assert skill.name is not None
            assert skill.description is not None
            assert skill.skill_type in list(SkillType)
            assert 0 <= skill.extraction_confidence <= 1
            assert isinstance(skill.is_executable, bool)

    @pytest.mark.asyncio
    async def test_confidence_filtering(self, sample_documents):
        """Test confidence-based filtering."""
        extractor = SkillExtractor()

        # Low threshold
        skills_low = await extractor.extract_skills(
            documents=sample_documents,
            category="operations",
            min_confidence=0.0,
        )

        # High threshold
        skills_high = await extractor.extract_skills(
            documents=sample_documents,
            category="operations",
            min_confidence=0.9,
        )

        # High confidence filter should give same or fewer skills
        assert len(skills_high) <= len(skills_low)


@pytest.mark.asyncio
async def test_end_to_end_extraction(sample_documents):
    """Test end-to-end skill extraction."""
    extractor = SkillExtractor()

    skills = await extractor.extract_skills(
        documents=sample_documents,
        category="operations",
        min_confidence=0.5,
    )

    assert isinstance(skills, list)
    assert len(skills) > 0

    # Convert to dict for API response
    skill_dicts = [s.to_dict() for s in skills]
    assert all(isinstance(d, dict) for d in skill_dicts)
    assert all("name" in d for d in skill_dicts)
    assert all("skill_type" in d for d in skill_dicts)
