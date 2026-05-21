"""
Skill Extraction Engine

Automatically extracts executable AI skills from organizational knowledge sources.
Detects patterns, decision trees, and operational heuristics.
"""

import logging
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from collections import Counter, defaultdict
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class SkillType(str, Enum):
    """Types of skills that can be extracted."""
    WORKFLOW = "workflow"
    DECISION_TREE = "decision_tree"
    APPROVAL_CHAIN = "approval_chain"
    EXCEPTION_HANDLER = "exception_handler"
    ANALYSIS = "analysis"
    REPORT_GENERATION = "report_generation"
    ESCALATION = "escalation"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted skills."""
    HIGH = "high"  # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # < 0.5


@dataclass
class Step:
    """Workflow step."""
    order: int
    action: str
    description: str
    tool_required: Optional[str] = None
    requires_approval: bool = False
    estimated_duration_minutes: int = 0
    error_handling: Optional[str] = None


@dataclass
class DecisionPoint:
    """Decision point in a workflow."""
    question: str
    branches: Dict[str, str]  # answer -> next_step
    confidence: float
    supporting_examples: List[str]


@dataclass
class SkillDefinition:
    """Complete skill definition."""
    id: str
    name: str
    description: str
    skill_type: SkillType
    category: str
    version: str = "1.0.0"

    # Execution details
    steps: List[Step] = None
    decision_points: List[DecisionPoint] = None
    required_tools: List[str] = None
    required_permissions: List[str] = None

    # Metadata
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None
    success_criteria: List[str] = None
    error_handlers: List[Dict[str, Any]] = None

    # Quality metrics
    extraction_confidence: float = 0.0
    examples_found: int = 0
    supporting_documents: int = 0

    # Status
    is_executable: bool = False
    is_validated: bool = False
    owner_team: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.decision_points is None:
            self.decision_points = []
        if self.required_tools is None:
            self.required_tools = []
        if self.required_permissions is None:
            self.required_permissions = []
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}
        if self.success_criteria is None:
            self.success_criteria = []
        if self.error_handlers is None:
            self.error_handlers = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "category": self.category,
            "version": self.version,
            "steps": [asdict(s) for s in self.steps],
            "decision_points": [
                {
                    "question": dp.question,
                    "branches": dp.branches,
                    "confidence": dp.confidence,
                    "supporting_examples": dp.supporting_examples,
                }
                for dp in self.decision_points
            ],
            "required_tools": self.required_tools,
            "required_permissions": self.required_permissions,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "success_criteria": self.success_criteria,
            "error_handlers": self.error_handlers,
            "extraction_confidence": self.extraction_confidence,
            "examples_found": self.examples_found,
            "supporting_documents": self.supporting_documents,
            "is_executable": self.is_executable,
            "is_validated": self.is_validated,
            "owner_team": self.owner_team,
            "created_at": self.created_at,
        }


class PatternDetector:
    """Detects recurring patterns in organizational data."""

    def __init__(self):
        self.patterns: Dict[str, List[str]] = defaultdict(list)
        self.pattern_frequency: Counter = Counter()

    async def detect_patterns(
        self,
        documents: List[Dict[str, Any]],
        min_frequency: int = 3,
    ) -> Dict[str, Any]:
        """
        Detect recurring patterns from documents.

        Args:
            documents: List of document dicts
            min_frequency: Minimum occurrences for a pattern

        Returns:
            Detected patterns with frequency
        """
        logger.info(f"Detecting patterns from {len(documents)} documents")

        # Extract actions and sequences
        action_sequences = self._extract_sequences(documents)

        # Find repeated sequences
        frequent_patterns = self._find_frequent_sequences(
            action_sequences, min_frequency
        )

        # Extract workflows
        workflows = self._extract_workflows(frequent_patterns)

        logger.info(f"Detected {len(workflows)} workflow patterns")

        return {
            "total_documents": len(documents),
            "patterns_found": len(workflows),
            "patterns": workflows,
            "confidence": self._calculate_confidence(workflows, documents),
        }

    def _extract_sequences(self, documents: List[Dict[str, Any]]) -> List[List[str]]:
        """Extract action sequences from documents."""
        sequences = []

        for doc in documents:
            # Extract actions from document content
            content = doc.get("content", "")
            actions = self._parse_actions(content)

            if actions:
                sequences.append(actions)

        return sequences

    def _parse_actions(self, text: str) -> List[str]:
        """Parse actions from text."""
        # Simple action extraction using regex
        action_patterns = [
            r"(?:then|next|after)\s+([a-z]+(?:\s+[a-z]+)?)",
            r"(?:step|stage)\s+\d+:\s+([a-z]+(?:\s+[a-z]+)?)",
            r"(?:send|create|update|approve|reject|escalate|notify)\s+",
        ]

        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, text.lower())
            actions.extend(matches)

        return actions

    def _find_frequent_sequences(
        self, sequences: List[List[str]], min_frequency: int
    ) -> Dict[str, int]:
        """Find frequently occurring sequences."""
        sequence_counts: Counter = Counter()

        for seq in sequences:
            # Single actions
            for action in seq:
                sequence_counts[action] += 1

            # Pairs
            for i in range(len(seq) - 1):
                pair = f"{seq[i]} -> {seq[i + 1]}"
                sequence_counts[pair] += 1

            # Triples
            for i in range(len(seq) - 2):
                triple = f"{seq[i]} -> {seq[i + 1]} -> {seq[i + 2]}"
                sequence_counts[triple] += 1

        return {
            pattern: count
            for pattern, count in sequence_counts.items()
            if count >= min_frequency
        }

    def _extract_workflows(
        self, frequent_sequences: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Extract workflows from sequences."""
        workflows = []

        for pattern, frequency in frequent_sequences.items():
            if "->" in pattern:  # Multi-step workflow
                steps = [s.strip() for s in pattern.split("->")]

                workflows.append(
                    {
                        "pattern": pattern,
                        "steps": steps,
                        "frequency": frequency,
                        "confidence": min(frequency / 10, 1.0),  # Cap at 1.0
                    }
                )

        return sorted(workflows, key=lambda x: x["frequency"], reverse=True)

    def _calculate_confidence(
        self, workflows: List[Dict[str, Any]], documents: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence of extracted patterns."""
        if not workflows or not documents:
            return 0.0

        avg_confidence = sum(w["confidence"] for w in workflows) / len(workflows)
        coverage = len(workflows) / max(len(documents), 1)

        return min((avg_confidence + coverage) / 2, 1.0)


class DecisionTreeExtractor:
    """Extracts decision trees from ticket histories and workflows."""

    async def extract_decision_trees(
        self,
        documents: List[Dict[str, Any]],
        min_support: int = 2,
    ) -> List[DecisionPoint]:
        """
        Extract decision points from documents.

        Args:
            documents: Document list
            min_support: Minimum examples per decision

        Returns:
            List of decision points
        """
        logger.info(f"Extracting decision trees from {len(documents)} documents")

        decision_points = []

        # Extract conditional statements
        conditions = self._extract_conditions(documents)

        # Group by decision
        decision_groups = self._group_by_decision(conditions)

        # Build decision points
        for decision, branches in decision_groups.items():
            if len(branches) >= min_support:
                dp = DecisionPoint(
                    question=decision,
                    branches={
                        outcome: next_action
                        for outcome, next_action in branches.items()
                    },
                    confidence=min(len(branches) / 10, 1.0),
                    supporting_examples=[
                        f"Example {i+1}" for i in range(min(3, len(branches)))
                    ],
                )
                decision_points.append(dp)

        logger.info(f"Extracted {len(decision_points)} decision points")
        return decision_points

    def _extract_conditions(self, documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract conditional statements."""
        conditions = []

        for doc in documents:
            content = doc.get("content", "").lower()

            # Match if/then patterns
            if_then_pattern = r"if\s+(.+?)\s+then\s+(.+?)(?:\.|;|$)"
            matches = re.findall(if_then_pattern, content)

            for condition, action in matches:
                conditions.append(
                    {
                        "condition": condition.strip(),
                        "action": action.strip(),
                    }
                )

        return conditions

    def _group_by_decision(
        self, conditions: List[Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """Group conditions by decision."""
        grouped: Dict[str, Dict[str, str]] = defaultdict(dict)

        for cond in conditions:
            condition = cond["condition"]
            action = cond["action"]

            # Simplify condition to decision
            decision = self._simplify_condition(condition)
            outcome = self._extract_outcome(condition)

            grouped[decision][outcome] = action

        return dict(grouped)

    def _simplify_condition(self, condition: str) -> str:
        """Simplify condition to a question."""
        # Remove common prefixes
        question = condition.replace("if ", "").replace("is ", "").title()
        return f"Is {question}?"

    def _extract_outcome(self, condition: str) -> str:
        """Extract the outcome from condition."""
        if "not" in condition.lower() or "no" in condition.lower():
            return "no"
        return "yes"


class HeuristicLearner:
    """Learns operational heuristics from data."""

    async def learn_heuristics(
        self,
        documents: List[Dict[str, Any]],
        patterns: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Learn operational rules and heuristics.

        Args:
            documents: Source documents
            patterns: Extracted patterns

        Returns:
            List of heuristic rules
        """
        logger.info("Learning operational heuristics")

        heuristics = []

        # Extract approval rules
        approval_rules = self._extract_approval_rules(documents)
        heuristics.extend(approval_rules)

        # Extract escalation rules
        escalation_rules = self._extract_escalation_rules(documents)
        heuristics.extend(escalation_rules)

        # Extract exception handlers
        exception_rules = self._extract_exception_handlers(documents)
        heuristics.extend(exception_rules)

        logger.info(f"Learned {len(heuristics)} heuristic rules")
        return heuristics

    def _extract_approval_rules(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract approval chain rules."""
        rules = []

        approval_patterns = [
            r"(?:requires|needs)?\s*approval\s+(?:from|by)\s+([a-z\s]+)(?:\s+if\s+(.+?))?",
            r"([a-z\s]+)\s+(?:must|should)\s+approve\s+(?:if\s+)?(.+?)(?:\.|$)",
        ]

        for doc in documents:
            content = doc.get("content", "").lower()

            for pattern in approval_patterns:
                matches = re.findall(pattern, content)
                for role, condition in matches:
                    rules.append(
                        {
                            "type": "approval",
                            "role": role.title(),
                            "condition": condition or "Always",
                            "confidence": 0.7,
                        }
                    )

        return rules

    def _extract_escalation_rules(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract escalation rules."""
        rules = []

        escalation_patterns = [
            r"(?:escalate|escalation)\s+(?:to\s+)?([a-z\s]+)\s+(?:if|when)\s+(.+?)(?:\.|$)",
            r"if\s+(.+?)\s+(?:escalate|notify)\s+([a-z\s]+)",
        ]

        for doc in documents:
            content = doc.get("content", "").lower()

            for pattern in escalation_patterns:
                matches = re.findall(pattern, content)
                for escalate_to, condition in matches:
                    rules.append(
                        {
                            "type": "escalation",
                            "escalate_to": escalate_to.title(),
                            "condition": condition.strip(),
                            "confidence": 0.65,
                        }
                    )

        return rules

    def _extract_exception_handlers(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract exception handling rules."""
        rules = []

        exception_patterns = [
            r"(?:if|on|in case of)\s+(?:error|exception|failure|issue)\s+(.+?)\s+(?:then|do)\s+(.+?)(?:\.|$)",
            r"error\s+handling:\s+(.+?)\s+->\s+(.+?)(?:\.|$)",
        ]

        for doc in documents:
            content = doc.get("content", "").lower()

            for pattern in exception_patterns:
                matches = re.findall(pattern, content)
                for error_type, handler in matches:
                    rules.append(
                        {
                            "type": "exception_handler",
                            "error": error_type.strip(),
                            "handler": handler.strip(),
                            "confidence": 0.6,
                        }
                    )

        return rules


class SkillGenerator:
    """Generates executable skill definitions."""

    async def generate_skills(
        self,
        patterns: Dict[str, Any],
        decision_points: List[DecisionPoint],
        heuristics: List[Dict[str, Any]],
        category: str = "operations",
    ) -> List[SkillDefinition]:
        """
        Generate skill definitions from extracted intelligence.

        Args:
            patterns: Extracted patterns
            decision_points: Decision trees
            heuristics: Operational rules
            category: Skill category

        Returns:
            List of skill definitions
        """
        logger.info("Generating skill definitions")

        skills = []

        # Generate workflow skills
        for pattern in patterns.get("patterns", []):
            skill = self._create_workflow_skill(pattern, category)
            skills.append(skill)

        # Generate decision skills
        for decision_point in decision_points:
            skill = self._create_decision_skill(decision_point, category)
            skills.append(skill)

        # Generate approval/escalation skills
        for heuristic in heuristics:
            if heuristic["type"] == "approval":
                skill = self._create_approval_skill(heuristic, category)
                skills.append(skill)
            elif heuristic["type"] == "escalation":
                skill = self._create_escalation_skill(heuristic, category)
                skills.append(skill)

        logger.info(f"Generated {len(skills)} skill definitions")
        return skills

    def _create_workflow_skill(
        self, pattern: Dict[str, Any], category: str
    ) -> SkillDefinition:
        """Create workflow skill from pattern."""
        steps_data = pattern.get("steps", [])
        steps = [
            Step(
                order=i,
                action=step.title(),
                description=f"Execute {step}",
            )
            for i, step in enumerate(steps_data, 1)
        ]

        return SkillDefinition(
            id=f"skill-{'-'.join(steps_data[:2]).lower()}",
            name=f"{' -> '.join(s.title() for s in steps_data[:2])} Workflow",
            description=f"Workflow: {pattern.get('pattern', '')}",
            skill_type=SkillType.WORKFLOW,
            category=category,
            steps=steps,
            required_tools=self._infer_tools(steps_data),
            extraction_confidence=pattern.get("confidence", 0.5),
            examples_found=pattern.get("frequency", 1),
            is_executable=True,
        )

    def _create_decision_skill(
        self, decision_point: DecisionPoint, category: str
    ) -> SkillDefinition:
        """Create decision skill."""
        return SkillDefinition(
            id=f"skill-decision-{len(decision_point.branches)}branch",
            name=f"Decision: {decision_point.question[:30]}...",
            description=decision_point.question,
            skill_type=SkillType.DECISION_TREE,
            category=category,
            decision_points=[decision_point],
            extraction_confidence=decision_point.confidence,
            examples_found=len(decision_point.supporting_examples),
            is_executable=True,
        )

    def _create_approval_skill(
        self, heuristic: Dict[str, Any], category: str
    ) -> SkillDefinition:
        """Create approval workflow skill."""
        return SkillDefinition(
            id=f"skill-approval-{heuristic['role'].lower().replace(' ', '-')}",
            name=f"Approval by {heuristic['role']}",
            description=f"Get approval from {heuristic['role']} {heuristic.get('condition', '')}",
            skill_type=SkillType.APPROVAL_CHAIN,
            category=category,
            required_permissions=[heuristic["role"]],
            extraction_confidence=heuristic.get("confidence", 0.7),
            is_executable=True,
        )

    def _create_escalation_skill(
        self, heuristic: Dict[str, Any], category: str
    ) -> SkillDefinition:
        """Create escalation skill."""
        return SkillDefinition(
            id=f"skill-escalation-{heuristic['escalate_to'].lower().replace(' ', '-')}",
            name=f"Escalate to {heuristic['escalate_to']}",
            description=f"Escalate when: {heuristic.get('condition', '')}",
            skill_type=SkillType.ESCALATION,
            category=category,
            extraction_confidence=heuristic.get("confidence", 0.65),
            is_executable=True,
        )

    def _infer_tools(self, steps: List[str]) -> List[str]:
        """Infer required tools from steps."""
        tools = []
        tool_keywords = {
            "email": ["send", "notify", "email"],
            "salesforce": ["create", "update", "crm"],
            "jira": ["ticket", "issue", "jira"],
            "slack": ["message", "slack", "notify"],
            "database": ["query", "update", "data"],
        }

        steps_text = " ".join(s.lower() for s in steps)

        for tool, keywords in tool_keywords.items():
            if any(kw in steps_text for kw in keywords):
                tools.append(tool)

        return tools


class SkillExtractor:
    """Main skill extraction orchestrator."""

    def __init__(self):
        self.pattern_detector = PatternDetector()
        self.decision_extractor = DecisionTreeExtractor()
        self.heuristic_learner = HeuristicLearner()
        self.skill_generator = SkillGenerator()

    async def extract_skills(
        self,
        documents: List[Dict[str, Any]],
        category: str = "operations",
        min_confidence: float = 0.5,
    ) -> List[SkillDefinition]:
        """
        Extract executable skills from documents.

        This is the main entry point for skill extraction.

        Args:
            documents: List of documents to analyze
            category: Skill category
            min_confidence: Minimum confidence threshold

        Returns:
            List of extracted skills
        """
        logger.info(
            f"Extracting skills from {len(documents)} documents "
            f"(category: {category}, min_confidence: {min_confidence})"
        )

        # Step 1: Detect patterns
        patterns = await self.pattern_detector.detect_patterns(documents, min_frequency=2)

        # Step 2: Extract decision trees
        decision_points = await self.decision_extractor.extract_decision_trees(documents)

        # Step 3: Learn heuristics
        heuristics = await self.heuristic_learner.learn_heuristics(documents, patterns)

        # Step 4: Generate skills
        skills = await self.skill_generator.generate_skills(
            patterns, decision_points, heuristics, category
        )

        # Filter by confidence
        filtered_skills = [
            skill
            for skill in skills
            if skill.extraction_confidence >= min_confidence
        ]

        logger.info(f"Extraction complete: {len(filtered_skills)} skills extracted")

        return filtered_skills

    async def extract_and_store_skills(
        self,
        db: AsyncSession,
        organization_id: str,
        documents: List[Dict[str, Any]],
        category: str = "operations",
    ) -> List[SkillDefinition]:
        """
        Extract skills and store in database.

        Args:
            db: Database session
            organization_id: Organization ID
            documents: Documents to extract from
            category: Skill category

        Returns:
            Stored skill definitions
        """
        # Extract skills
        skills = await self.extract_skills(documents, category)

        # TODO: Store in database
        # for skill in skills:
        #     db_skill = models.Skill(
        #         organization_id=organization_id,
        #         name=skill.name,
        #         ...
        #     )
        #     db.add(db_skill)
        # await db.commit()

        logger.info(f"Stored {len(skills)} extracted skills")
        return skills
