"""
Memory Consolidation Engine

Consolidates, deduplicates, and ranks organizational memory.
Implements episodic, semantic, and procedural memory systems.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import difflib
import json

logger = logging.getLogger(__name__)


@dataclass
class Fact:
    """Semantic fact in memory."""
    id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)
    frequency: int = 1
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "sources": self.sources,
            "frequency": self.frequency,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ConflictResolution:
    """Resolution of conflicting facts."""
    fact1: Fact
    fact2: Fact
    resolution: str  # "merge", "keep_first", "keep_second", "flag_conflict"
    confidence: float
    reasoning: str


class FactMerger:
    """Merges related facts."""

    async def merge_facts(
        self,
        facts: List[Fact],
        similarity_threshold: float = 0.8,
    ) -> List[Fact]:
        """
        Merge similar facts.

        Args:
            facts: List of facts to merge
            similarity_threshold: Minimum similarity for merging

        Returns:
            Merged facts
        """
        logger.info(f"Merging {len(facts)} facts")

        # Find similar facts
        merged = []
        used_indices = set()

        for i, fact1 in enumerate(facts):
            if i in used_indices:
                continue

            # Find all similar facts
            similar = [fact1]
            for j, fact2 in enumerate(facts[i + 1 :], start=i + 1):
                if j not in used_indices:
                    similarity = self._calculate_similarity(fact1, fact2)
                    if similarity >= similarity_threshold:
                        similar.append(fact2)
                        used_indices.add(j)

            # Merge similar facts
            if len(similar) > 1:
                merged_fact = self._merge_fact_group(similar)
                merged.append(merged_fact)
            else:
                merged.append(fact1)

            used_indices.add(i)

        logger.info(f"Merged to {len(merged)} facts")
        return merged

    def _calculate_similarity(self, fact1: Fact, fact2: Fact) -> float:
        """Calculate similarity between facts."""
        # Compare subject, predicate, object
        subject_sim = difflib.SequenceMatcher(None, fact1.subject, fact2.subject).ratio()
        predicate_sim = difflib.SequenceMatcher(
            None, fact1.predicate, fact2.predicate
        ).ratio()
        object_sim = difflib.SequenceMatcher(None, fact1.object, fact2.object).ratio()

        # Average similarity
        return (subject_sim + predicate_sim + object_sim) / 3

    def _merge_fact_group(self, facts: List[Fact]) -> Fact:
        """Merge a group of similar facts."""
        # Use the fact with highest confidence as base
        base = max(facts, key=lambda f: f.confidence)

        # Combine metadata
        merged_fact = Fact(
            id=base.id,
            subject=base.subject,
            predicate=base.predicate,
            object=base.object,
            confidence=min(
                max(f.confidence for f in facts), 1.0
            ),  # Cap at 1.0
            sources=list(set().union(*[f.sources for f in facts])),
            frequency=sum(f.frequency for f in facts),
            last_accessed=max(
                (f.last_accessed for f in facts if f.last_accessed),
                default=datetime.utcnow(),
            ),
        )

        return merged_fact


class ConflictResolver:
    """Resolves conflicts between facts."""

    async def resolve_conflicts(
        self,
        facts: List[Fact],
    ) -> Tuple[List[Fact], List[ConflictResolution]]:
        """
        Identify and resolve conflicting facts.

        Args:
            facts: List of facts

        Returns:
            Resolved facts and conflict resolutions
        """
        logger.info(f"Resolving conflicts in {len(facts)} facts")

        conflicts = []
        resolved_facts = list(facts)

        # Find contradictory facts
        for i, fact1 in enumerate(facts):
            for fact2 in facts[i + 1 :]:
                if self._are_contradictory(fact1, fact2):
                    # Attempt resolution
                    resolution = self._resolve_conflict(fact1, fact2)
                    conflicts.append(resolution)

                    # Apply resolution
                    if resolution.resolution == "merge":
                        # Merge them
                        merged = self._merge_conflicting(fact1, fact2)
                        resolved_facts.remove(fact1)
                        resolved_facts.remove(fact2)
                        resolved_facts.append(merged)
                    elif resolution.resolution == "keep_first":
                        resolved_facts.remove(fact2)
                    elif resolution.resolution == "keep_second":
                        resolved_facts.remove(fact1)
                    # "flag_conflict" keeps both

        logger.info(f"Resolved {len(conflicts)} conflicts")
        return resolved_facts, conflicts

    def _are_contradictory(self, fact1: Fact, fact2: Fact) -> bool:
        """Check if facts contradict."""
        # Same subject and predicate but different object = contradiction
        return (
            fact1.subject.lower() == fact2.subject.lower()
            and fact1.predicate.lower() == fact2.predicate.lower()
            and fact1.object.lower() != fact2.object.lower()
        )

    def _resolve_conflict(self, fact1: Fact, fact2: Fact) -> ConflictResolution:
        """Resolve a conflict."""
        # Use confidence to decide
        if fact1.confidence > fact2.confidence:
            resolution = "keep_first"
        elif fact2.confidence > fact1.confidence:
            resolution = "keep_second"
        else:
            # Same confidence - try to merge
            resolution = "merge"

        return ConflictResolution(
            fact1=fact1,
            fact2=fact2,
            resolution=resolution,
            confidence=max(fact1.confidence, fact2.confidence),
            reasoning=f"Confidence-based resolution: {fact1.confidence} vs {fact2.confidence}",
        )

    def _merge_conflicting(self, fact1: Fact, fact2: Fact) -> Fact:
        """Merge conflicting facts."""
        # Create a new fact with both objects as list
        merged_object = f"{fact1.object} or {fact2.object}"

        return Fact(
            id=f"{fact1.id}-merged",
            subject=fact1.subject,
            predicate=fact1.predicate,
            object=merged_object,
            confidence=(fact1.confidence + fact2.confidence) / 2,
            sources=list(set(fact1.sources + fact2.sources)),
            frequency=fact1.frequency + fact2.frequency,
        )


class RelevanceScorer:
    """Scores relevance of facts."""

    async def score_relevance(
        self,
        facts: List[Fact],
        recency_weight: float = 0.3,
        frequency_weight: float = 0.3,
        confidence_weight: float = 0.4,
    ) -> Dict[str, float]:
        """
        Score relevance of facts.

        Args:
            facts: List of facts
            recency_weight: Weight for recency
            frequency_weight: Weight for frequency
            confidence_weight: Weight for confidence

        Returns:
            Fact ID to relevance score mapping
        """
        logger.info(f"Scoring relevance of {len(facts)} facts")

        scores = {}

        for fact in facts:
            # Recency score (0-1)
            days_old = (datetime.utcnow() - fact.created_at).days
            recency = max(0, 1 - (days_old / 365))  # Decay over 1 year

            # Frequency score (normalized)
            max_freq = max((f.frequency for f in facts), default=1)
            frequency = fact.frequency / max_freq if max_freq > 0 else 0

            # Confidence score (already 0-1)
            confidence = fact.confidence

            # Weighted average
            relevance = (
                recency_weight * recency
                + frequency_weight * frequency
                + confidence_weight * confidence
            )

            scores[fact.id] = relevance

        return scores

    async def filter_by_relevance(
        self,
        facts: List[Fact],
        min_relevance: float = 0.5,
    ) -> List[Fact]:
        """
        Filter facts by minimum relevance.

        Args:
            facts: List of facts
            min_relevance: Minimum relevance threshold

        Returns:
            Filtered facts
        """
        scores = await self.score_relevance(facts)

        filtered = [f for f in facts if scores.get(f.id, 0) >= min_relevance]

        logger.info(f"Filtered to {len(filtered)} relevant facts")
        return filtered


class DecayCalculator:
    """Calculates and applies memory decay."""

    async def calculate_decay(
        self,
        facts: List[Fact],
        base_decay_rate: float = 0.01,  # 1% per day
        min_confidence: float = 0.1,
    ) -> List[Fact]:
        """
        Apply decay to fact confidence over time.

        Args:
            facts: List of facts
            base_decay_rate: Daily decay rate
            min_confidence: Minimum confidence threshold

        Returns:
            Facts with updated confidence
        """
        logger.info(f"Calculating decay for {len(facts)} facts")

        decayed = []

        for fact in facts:
            days_old = (datetime.utcnow() - fact.created_at).days

            # Exponential decay: confidence *= (1 - rate)^days
            new_confidence = fact.confidence * ((1 - base_decay_rate) ** days_old)
            new_confidence = max(new_confidence, min_confidence)  # Floor at min

            decayed_fact = Fact(
                id=fact.id,
                subject=fact.subject,
                predicate=fact.predicate,
                object=fact.object,
                confidence=new_confidence,
                sources=fact.sources,
                frequency=fact.frequency,
                last_accessed=fact.last_accessed,
                created_at=fact.created_at,
            )

            decayed.append(decayed_fact)

        return decayed

    async def refresh_fact(self, fact: Fact) -> Fact:
        """
        Refresh a fact's timestamp and increase confidence.

        Args:
            fact: Fact to refresh

        Returns:
            Updated fact
        """
        refreshed = Fact(
            id=fact.id,
            subject=fact.subject,
            predicate=fact.predicate,
            object=fact.object,
            confidence=min(fact.confidence + 0.05, 1.0),  # Boost by 5%
            sources=fact.sources,
            frequency=fact.frequency + 1,
            last_accessed=datetime.utcnow(),
            created_at=fact.created_at,
        )

        return refreshed


class MemoryConsolidator:
    """Main memory consolidation orchestrator."""

    def __init__(self):
        self.fact_merger = FactMerger()
        self.conflict_resolver = ConflictResolver()
        self.relevance_scorer = RelevanceScorer()
        self.decay_calculator = DecayCalculator()

    async def consolidate_memory(
        self,
        facts: List[Fact],
        apply_decay: bool = True,
        min_relevance: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Consolidate organizational memory.

        This performs deduplication, conflict resolution, and cleanup.

        Args:
            facts: Raw facts from sources
            apply_decay: Apply temporal decay
            min_relevance: Minimum relevance to keep

        Returns:
            Consolidation report with stats
        """
        logger.info(f"Consolidating {len(facts)} facts")

        original_count = len(facts)

        # Step 1: Merge similar facts
        merged = await self.fact_merger.merge_facts(facts)
        merged_count = len(merged)

        # Step 2: Resolve conflicts
        resolved, conflicts = await self.conflict_resolver.resolve_conflicts(merged)
        resolved_count = len(resolved)

        # Step 3: Apply decay
        if apply_decay:
            decayed = await self.decay_calculator.calculate_decay(resolved)
        else:
            decayed = resolved

        # Step 4: Filter by relevance
        final = await self.relevance_scorer.filter_by_relevance(
            decayed, min_relevance
        )
        final_count = len(final)

        # Score final facts
        scores = await self.relevance_scorer.score_relevance(final)

        logger.info(
            f"Consolidation complete: {original_count} → {final_count} facts"
        )

        return {
            "original_count": original_count,
            "merged_count": merged_count,
            "resolved_count": resolved_count,
            "final_count": final_count,
            "conflicts_found": len(conflicts),
            "duplicates_removed": original_count - merged_count,
            "consolidation_ratio": final_count / original_count if original_count > 0 else 0,
            "facts": final,
            "fact_scores": scores,
            "conflicts": [
                {
                    "fact1": c.fact1.to_dict(),
                    "fact2": c.fact2.to_dict(),
                    "resolution": c.resolution,
                    "reasoning": c.reasoning,
                }
                for c in conflicts
            ],
        }

    async def learn_from_facts(
        self,
        facts: List[Fact],
    ) -> Dict[str, Any]:
        """
        Learn relationships and patterns from consolidated facts.

        Args:
            facts: Consolidated facts

        Returns:
            Learned patterns and insights
        """
        logger.info(f"Learning from {len(facts)} facts")

        # Count predicates (relationships)
        predicate_counts = Counter(f.predicate for f in facts)

        # Find most confident facts
        top_facts = sorted(facts, key=lambda f: f.confidence, reverse=True)[:10]

        # Find frequently mentioned subjects
        subject_counts = Counter(f.subject for f in facts)

        # Find frequently mentioned objects
        object_counts = Counter(f.object for f in facts)

        return {
            "total_facts": len(facts),
            "unique_subjects": len(set(f.subject for f in facts)),
            "unique_predicates": len(set(f.predicate for f in facts)),
            "unique_objects": len(set(f.object for f in facts)),
            "most_common_relationships": predicate_counts.most_common(5),
            "most_confident_facts": [f.to_dict() for f in top_facts],
            "most_mentioned_subjects": subject_counts.most_common(5),
            "most_mentioned_objects": object_counts.most_common(5),
            "average_confidence": sum(f.confidence for f in facts) / len(facts)
            if facts
            else 0,
        }
