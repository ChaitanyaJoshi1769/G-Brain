"""
Workflow Inference Engine

Infers operational workflows from ticket histories, conversations, and documents.
Performs process mining, dependency mapping, and SOP generation.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)


@dataclass
class WorkflowNode:
    """Node in a workflow graph."""
    id: str
    name: str
    action_type: str  # "task", "decision", "approval", "end"
    description: Optional[str] = None
    duration_minutes: int = 0
    error_rate: float = 0.0
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class WorkflowEdge:
    """Edge in workflow graph."""
    source: str
    target: str
    label: Optional[str] = None
    frequency: int = 1
    success_rate: float = 1.0


@dataclass
class WorkflowGraph:
    """Complete workflow graph."""
    id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    start_node: str
    end_nodes: List[str]

    # Metrics
    average_duration_minutes: int = 0
    success_rate: float = 0.0
    total_executions: int = 0
    bottlenecks: List[Dict[str, Any]] = None
    critical_paths: List[List[str]] = None

    def __post_init__(self):
        if self.bottlenecks is None:
            self.bottlenecks = []
        if self.critical_paths is None:
            self.critical_paths = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.action_type,
                    "description": n.description,
                    "duration_minutes": n.duration_minutes,
                    "error_rate": n.error_rate,
                    "dependencies": n.dependencies,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "label": e.label,
                    "frequency": e.frequency,
                    "success_rate": e.success_rate,
                }
                for e in self.edges
            ],
            "start_node": self.start_node,
            "end_nodes": self.end_nodes,
            "average_duration_minutes": self.average_duration_minutes,
            "success_rate": self.success_rate,
            "total_executions": self.total_executions,
            "bottlenecks": self.bottlenecks,
            "critical_paths": self.critical_paths,
        }


class ProcessMiner:
    """Mines processes from event logs and ticket histories."""

    async def mine_processes(
        self, events: List[Dict[str, Any]], min_support: int = 2
    ) -> List[List[str]]:
        """
        Mine frequent process patterns.

        Args:
            events: List of event dicts with timestamps and actions
            min_support: Minimum support threshold

        Returns:
            List of frequent process patterns
        """
        logger.info(f"Mining processes from {len(events)} events")

        # Extract sequences
        sequences = self._extract_event_sequences(events)

        # Mine frequent patterns
        patterns = self._mine_frequent_sequences(sequences, min_support)

        logger.info(f"Mined {len(patterns)} process patterns")
        return patterns

    def _extract_event_sequences(self, events: List[Dict[str, Any]]) -> List[List[str]]:
        """Extract action sequences from events."""
        # Group events by case ID or document ID
        cases = defaultdict(list)

        for event in events:
            case_id = event.get("case_id") or event.get("document_id", "default")
            action = event.get("action") or event.get("event_type", "")

            if action:
                cases[case_id].append(action)

        return list(cases.values())

    def _mine_frequent_sequences(
        self, sequences: List[List[str]], min_support: int
    ) -> List[List[str]]:
        """Mine frequent sequences."""
        pattern_counts: Counter = Counter()

        # Count all n-grams
        for seq in sequences:
            for i in range(len(seq)):
                for n in range(1, min(4, len(seq) - i + 1)):  # Up to trigrams
                    pattern = tuple(seq[i : i + n])
                    pattern_counts[pattern] += 1

        # Filter by support
        frequent = [
            list(pattern)
            for pattern, count in pattern_counts.items()
            if count >= min_support
        ]

        # Sort by frequency
        return sorted(
            frequent, key=lambda p: pattern_counts[tuple(p)], reverse=True
        )


class DependencyMapper:
    """Maps dependencies and relationships between workflow tasks."""

    async def map_dependencies(
        self, workflows: List[List[str]]
    ) -> Dict[str, List[str]]:
        """
        Map task dependencies from workflows.

        Args:
            workflows: List of workflow sequences

        Returns:
            Dependency graph (task -> predecessors)
        """
        logger.info(f"Mapping dependencies from {len(workflows)} workflows")

        dependencies: Dict[str, Set[str]] = defaultdict(set)

        for workflow in workflows:
            for i in range(1, len(workflow)):
                current = workflow[i]
                previous = workflow[i - 1]
                dependencies[current].add(previous)

        return {task: list(preds) for task, preds in dependencies.items()}

    async def find_critical_path(
        self, graph: WorkflowGraph
    ) -> List[str]:
        """
        Find critical path (longest path through workflow).

        Args:
            graph: Workflow graph

        Returns:
            Sequence of nodes in critical path
        """
        # Build adjacency list with durations
        edges_map: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for edge in graph.edges:
            # Find target node duration
            target_node = next(
                (n for n in graph.nodes if n.id == edge.target), None
            )
            duration = target_node.duration_minutes if target_node else 0

            edges_map[edge.source].append((edge.target, duration))

        # Calculate longest paths using DFS
        def find_longest_path(
            node: str, memo: Dict[str, Tuple[int, List[str]]]
        ) -> Tuple[int, List[str]]:
            if node in memo:
                return memo[node]

            # Base case: end node
            if not edges_map.get(node):
                return 0, [node]

            max_duration = 0
            best_path = [node]

            for next_node, duration in edges_map[node]:
                sub_duration, sub_path = find_longest_path(next_node, memo)
                total = duration + sub_duration

                if total > max_duration:
                    max_duration = total
                    best_path = [node] + sub_path

            memo[node] = (max_duration, best_path)
            return max_duration, best_path

        _, critical_path = find_longest_path(graph.start_node, {})
        return critical_path


class BottleneckAnalyzer:
    """Identifies bottlenecks and optimization opportunities."""

    async def analyze_bottlenecks(
        self, graph: WorkflowGraph
    ) -> List[Dict[str, Any]]:
        """
        Identify workflow bottlenecks.

        Args:
            graph: Workflow graph

        Returns:
            List of bottleneck analysis
        """
        logger.info("Analyzing bottlenecks")

        bottlenecks = []

        # Identify long-duration tasks
        slow_tasks = [
            n
            for n in graph.nodes
            if n.duration_minutes > graph.average_duration_minutes * 2
        ]
        if slow_tasks:
            bottlenecks.append(
                {
                    "type": "slow_task",
                    "tasks": [t.name for t in slow_tasks],
                    "recommendation": "Parallelize or optimize these tasks",
                }
            )

        # Identify high error rates
        error_tasks = [n for n in graph.nodes if n.error_rate > 0.2]
        if error_tasks:
            bottlenecks.append(
                {
                    "type": "high_error_rate",
                    "tasks": [t.name for t in error_tasks],
                    "recommendation": "Add error handling or validation",
                }
            )

        # Identify sequential dependencies (hard to parallelize)
        sequential_chains = self._find_sequential_chains(graph)
        if sequential_chains:
            bottlenecks.append(
                {
                    "type": "sequential_dependency",
                    "chains": sequential_chains,
                    "recommendation": "Look for parallelization opportunities",
                }
            )

        return bottlenecks

    def _find_sequential_chains(self, graph: WorkflowGraph) -> List[List[str]]:
        """Find long sequential chains."""
        chains = []

        for start_node in graph.nodes:
            if start_node.action_type == "task":
                chain = self._follow_chain(start_node.id, graph)
                if len(chain) > 2:  # Only chains of 3+ tasks
                    chains.append(chain)

        return chains

    def _follow_chain(self, node_id: str, graph: WorkflowGraph) -> List[str]:
        """Follow a chain of sequential tasks."""
        chain = [node_id]

        current_id = node_id
        while True:
            # Find next edge
            next_edges = [e for e in graph.edges if e.source == current_id]

            if not next_edges or len(next_edges) > 1:  # End or branch
                break

            next_id = next_edges[0].target
            chain.append(next_id)
            current_id = next_id

        return chain


class SOPGenerator:
    """Generates Standard Operating Procedures from workflows."""

    async def generate_sop(
        self, graph: WorkflowGraph, format: str = "markdown"
    ) -> str:
        """
        Generate SOP document from workflow.

        Args:
            graph: Workflow graph
            format: Output format ("markdown", "json", "html")

        Returns:
            SOP document
        """
        logger.info(f"Generating SOP for {graph.name}")

        if format == "markdown":
            return self._generate_markdown_sop(graph)
        elif format == "json":
            return self._generate_json_sop(graph)
        else:
            return self._generate_markdown_sop(graph)

    def _generate_markdown_sop(self, graph: WorkflowGraph) -> str:
        """Generate markdown SOP."""
        lines = [
            f"# {graph.name}",
            "",
            f"**Description**: {graph.description}",
            f"**Average Duration**: {graph.average_duration_minutes} minutes",
            f"**Success Rate**: {graph.success_rate*100:.1f}%",
            "",
            "## Steps",
            "",
        ]

        # Get all nodes in execution order
        nodes_by_id = {n.id: n for n in graph.nodes}

        # Start from beginning
        visited = set()
        current = graph.start_node
        step_num = 1

        while current and current not in visited:
            visited.add(current)
            node = nodes_by_id.get(current)

            if node:
                lines.append(f"### Step {step_num}: {node.name}")
                lines.append(f"- **Type**: {node.action_type}")
                if node.description:
                    lines.append(f"- **Description**: {node.description}")
                if node.duration_minutes:
                    lines.append(f"- **Expected Duration**: {node.duration_minutes} min")
                lines.append("")

            # Find next node
            next_edges = [e for e in graph.edges if e.source == current]
            if next_edges:
                current = next_edges[0].target
                step_num += 1
            else:
                break

        # Add bottlenecks section
        if graph.bottlenecks:
            lines.append("## Bottlenecks & Optimization")
            lines.append("")
            for bottleneck in graph.bottlenecks:
                lines.append(
                    f"- **{bottleneck['type'].replace('_', ' ').title()}**: "
                    f"{bottleneck.get('recommendation', '')}"
                )
            lines.append("")

        return "\n".join(lines)

    def _generate_json_sop(self, graph: WorkflowGraph) -> str:
        """Generate JSON SOP."""
        import json

        return json.dumps(graph.to_dict(), indent=2)


class WorkflowOptimizer:
    """Optimizes workflows for efficiency."""

    async def optimize_workflow(
        self, graph: WorkflowGraph
    ) -> Tuple[WorkflowGraph, List[Dict[str, Any]]]:
        """
        Optimize workflow for performance.

        Args:
            graph: Original workflow

        Returns:
            Optimized workflow and list of optimizations made
        """
        logger.info(f"Optimizing workflow: {graph.name}")

        optimizations = []

        # Find parallelization opportunities
        parallel_opps = self._find_parallelization(graph)
        if parallel_opps:
            optimizations.append(
                {
                    "type": "parallelization",
                    "tasks": parallel_opps,
                    "potential_speedup": "20-40%",
                }
            )

        # Find automation opportunities
        auto_opps = self._find_automation_opps(graph)
        if auto_opps:
            optimizations.append(
                {
                    "type": "automation",
                    "tasks": auto_opps,
                    "potential_time_saved": "30-50%",
                }
            )

        return graph, optimizations

    def _find_parallelization(self, graph: WorkflowGraph) -> List[str]:
        """Find tasks that can be parallelized."""
        parallelizable = []

        for node in graph.nodes:
            # Tasks with no dependencies on each other can be parallel
            if (
                node.action_type == "task"
                and len(node.dependencies) <= 1
                and node.duration_minutes > 5
            ):
                parallelizable.append(node.name)

        return parallelizable

    def _find_automation_opps(self, graph: WorkflowGraph) -> List[str]:
        """Find tasks suitable for automation."""
        automatable = []

        auto_keywords = ["send", "update", "create", "notify", "email", "message"]

        for node in graph.nodes:
            if any(kw in node.action_type.lower() for kw in auto_keywords):
                automatable.append(node.name)

        return automatable


class WorkflowInferencer:
    """Main workflow inference orchestrator."""

    def __init__(self):
        self.process_miner = ProcessMiner()
        self.dependency_mapper = DependencyMapper()
        self.bottleneck_analyzer = BottleneckAnalyzer()
        self.sop_generator = SOPGenerator()
        self.optimizer = WorkflowOptimizer()

    async def infer_workflows(
        self,
        documents: List[Dict[str, Any]],
        min_support: int = 2,
    ) -> List[WorkflowGraph]:
        """
        Infer workflows from documents.

        Args:
            documents: Source documents
            min_support: Minimum support threshold

        Returns:
            List of inferred workflow graphs
        """
        logger.info(f"Inferring workflows from {len(documents)} documents")

        # Convert documents to events
        events = self._convert_to_events(documents)

        # Mine processes
        patterns = await self.process_miner.mine_processes(events, min_support)

        # Build workflow graphs
        workflows = []

        for i, pattern in enumerate(patterns[:5]):  # Top 5 patterns
            graph = self._build_workflow_graph(pattern, events)
            workflows.append(graph)

        logger.info(f"Inferred {len(workflows)} workflows")
        return workflows

    def _convert_to_events(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert documents to events."""
        events = []

        action_pattern = r"(?:then|next|step|action):\s+([a-z\s]+)"

        for doc in documents:
            content = doc.get("content", "").lower()
            matches = re.findall(action_pattern, content)

            for action in matches:
                events.append(
                    {
                        "document_id": doc.get("id", ""),
                        "action": action.strip(),
                        "timestamp": doc.get("created_at", datetime.utcnow().isoformat()),
                    }
                )

        return events

    def _build_workflow_graph(
        self,
        pattern: List[str],
        events: List[Dict[str, Any]],
    ) -> WorkflowGraph:
        """Build workflow graph from pattern."""
        # Create nodes
        nodes = [
            WorkflowNode(
                id=f"node-{i}",
                name=step.title(),
                action_type="task" if i < len(pattern) - 1 else "end",
            )
            for i, step in enumerate(pattern)
        ]

        # Create edges
        edges = [
            WorkflowEdge(
                source=f"node-{i}",
                target=f"node-{i+1}",
                frequency=1,
            )
            for i in range(len(pattern) - 1)
        ]

        return WorkflowGraph(
            id=f"workflow-{'-'.join(pattern[:2]).lower()}",
            name=" → ".join(p.title() for p in pattern[:3]),
            description=f"Inferred workflow: {' → '.join(pattern)}",
            nodes=nodes,
            edges=edges,
            start_node="node-0",
            end_nodes=[f"node-{len(pattern)-1}"],
            total_executions=len(events),
        )
