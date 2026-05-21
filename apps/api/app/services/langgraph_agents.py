"""
LangGraph-Based Agent Framework

Implements stateful, persistent agent workflows using LangGraph.
Enables complex reasoning chains, memory management, and tool orchestration.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, TypedDict, Annotated, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class ThinkingStep(str, Enum):
    """Agent thinking steps in a reasoning chain."""
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    DECIDE = "decide"


class ReasoningMode(str, Enum):
    """Agent reasoning modes."""
    DIRECT = "direct"  # Execute immediately
    CHAIN_OF_THOUGHT = "chain_of_thought"  # Multi-step reasoning
    TREE_OF_THOUGHT = "tree_of_thought"  # Explore multiple paths
    REFLECTIVE = "reflective"  # Reason and reflect


@dataclass
class AgentMemory:
    """Agent's working memory."""
    short_term: Dict[str, Any] = field(default_factory=dict)  # Current context
    long_term: List[Dict[str, Any]] = field(default_factory=list)  # History
    facts: Dict[str, Any] = field(default_factory=dict)  # Learned facts
    max_short_term: int = 10
    max_long_term: int = 100

    def store_short_term(self, key: str, value: Any) -> None:
        """Store in short-term memory."""
        self.short_term[key] = value
        if len(self.short_term) > self.max_short_term:
            # Promote oldest to long-term
            oldest = next(iter(self.short_term))
            self.long_term.append({key: oldest, "value": self.short_term[oldest]})
            del self.short_term[oldest]

    def retrieve_short_term(self, key: str) -> Optional[Any]:
        """Retrieve from short-term memory."""
        return self.short_term.get(key)

    def store_fact(self, fact_key: str, fact_value: Any) -> None:
        """Store a learned fact."""
        self.facts[fact_key] = {"value": fact_value, "learned_at": datetime.utcnow()}

    def get_facts(self) -> Dict[str, Any]:
        """Get all learned facts."""
        return {k: v["value"] for k, v in self.facts.items()}


@dataclass
class ThinkingChainStep:
    """Step in a thinking chain."""
    step_type: ThinkingStep
    input_data: Dict[str, Any]
    output: Dict[str, Any]
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.5


@dataclass
class AgentState(TypedDict, total=False):
    """State for LangGraph agent workflow."""
    agent_id: str
    current_task: str
    status: str  # "thinking", "executing", "waiting", "completed"
    messages: List[Dict[str, Any]]  # Conversation history
    thinking_chain: List[ThinkingChainStep]  # Reasoning chain
    tool_calls: List[Dict[str, Any]]  # Executed tools
    working_memory: Dict[str, Any]  # Current context
    context: Dict[str, Any]  # External context
    metadata: Dict[str, Any]  # Additional info


class ToolUseNode:
    """Graph node for tool usage."""

    def __init__(self, tool_name: str, tool_fn: Callable):
        self.tool_name = tool_name
        self.tool_fn = tool_fn
        self.execution_count = 0
        self.average_duration_ms = 0.0

    async def execute(
        self, state: AgentState, **kwargs
    ) -> Tuple[AgentState, Dict[str, Any]]:
        """Execute the tool."""
        logger.info(f"Executing tool: {self.tool_name}")

        try:
            import time

            start = time.time()
            result = await self.tool_fn(**kwargs)
            duration = (time.time() - start) * 1000

            self.execution_count += 1
            self.average_duration_ms = (
                self.average_duration_ms * (self.execution_count - 1) + duration
            ) / self.execution_count

            state["tool_calls"].append(
                {
                    "tool": self.tool_name,
                    "status": "success",
                    "result": result,
                    "duration_ms": duration,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            return state, result

        except Exception as e:
            logger.error(f"Tool execution failed: {self.tool_name}", exc_info=True)
            state["tool_calls"].append(
                {
                    "tool": self.tool_name,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            return state, {"error": str(e)}


class ThinkingNode:
    """Graph node for agent thinking/reasoning."""

    def __init__(self, reasoning_mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT):
        self.reasoning_mode = reasoning_mode
        self.thinking_history: List[ThinkingChainStep] = []

    async def think(self, state: AgentState) -> AgentState:
        """Process thinking step."""
        logger.info(f"Agent thinking (mode={self.reasoning_mode.value})")

        task = state.get("current_task", "")
        messages = state.get("messages", [])
        working_memory = state.get("working_memory", {})

        # Simulate thinking process
        reasoning_output = await self._reason(
            task, messages, working_memory
        )

        # Create thinking chain step
        step = ThinkingChainStep(
            step_type=ThinkingStep.ANALYZE,
            input_data={"task": task, "context": working_memory},
            output=reasoning_output,
            reasoning=reasoning_output.get("reasoning", ""),
            confidence=reasoning_output.get("confidence", 0.5),
        )

        state["thinking_chain"].append(step)
        state["working_memory"].update(reasoning_output.get("updates", {}))

        return state

    async def _reason(
        self,
        task: str,
        messages: List[Dict[str, Any]],
        working_memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate reasoning."""
        if self.reasoning_mode == ReasoningMode.DIRECT:
            return {
                "reasoning": f"Direct execution of: {task}",
                "confidence": 0.9,
                "updates": {},
            }
        elif self.reasoning_mode == ReasoningMode.CHAIN_OF_THOUGHT:
            return {
                "reasoning": f"Step-by-step reasoning for: {task}",
                "confidence": 0.7,
                "steps": ["analyze", "plan", "execute"],
                "updates": {},
            }
        else:
            return {
                "reasoning": f"Reasoning in {self.reasoning_mode.value} mode",
                "confidence": 0.5,
                "updates": {},
            }


class DecisionNode:
    """Graph node for agent decision making."""

    async def decide(
        self,
        state: AgentState,
        options: List[str],
        decision_fn: Optional[Callable] = None,
    ) -> Tuple[AgentState, str]:
        """Make a decision between options."""
        logger.info(f"Making decision between: {options}")

        if decision_fn:
            choice = await decision_fn(state, options)
        else:
            # Default: choose first option
            choice = options[0] if options else "continue"

        state["messages"].append(
            {
                "role": "system",
                "content": f"Decision made: {choice}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return state, choice


class LangGraphAgentBuilder:
    """Builds LangGraph-based agents."""

    def __init__(self, agent_id: str, reasoning_mode: ReasoningMode):
        self.agent_id = agent_id
        self.reasoning_mode = reasoning_mode
        self.nodes: Dict[str, Any] = {}
        self.edges: List[Tuple[str, str]] = []
        self.tools: Dict[str, ToolUseNode] = {}
        self.memory = AgentMemory()

    def add_thinking_node(self, node_id: str) -> "LangGraphAgentBuilder":
        """Add a thinking/reasoning node."""
        self.nodes[node_id] = ThinkingNode(self.reasoning_mode)
        return self

    def add_tool_node(
        self, node_id: str, tool_name: str, tool_fn: Callable
    ) -> "LangGraphAgentBuilder":
        """Add a tool execution node."""
        self.nodes[node_id] = ToolUseNode(tool_name, tool_fn)
        self.tools[node_id] = self.nodes[node_id]
        return self

    def add_decision_node(self, node_id: str) -> "LangGraphAgentBuilder":
        """Add a decision node."""
        self.nodes[node_id] = DecisionNode()
        return self

    def add_edge(self, from_node: str, to_node: str) -> "LangGraphAgentBuilder":
        """Add an edge between nodes."""
        self.edges.append((from_node, to_node))
        return self

    def add_conditional_edge(
        self,
        from_node: str,
        condition_fn: Callable,
        paths: Dict[str, str],
    ) -> "LangGraphAgentBuilder":
        """Add a conditional edge."""
        # Store conditional routing logic
        if not hasattr(self, "_conditional_edges"):
            self._conditional_edges = {}
        self._conditional_edges[(from_node, condition_fn)] = paths
        return self

    async def build_and_execute(
        self, initial_task: str, initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build and execute the agent workflow."""
        logger.info(f"Building and executing agent: {self.agent_id}")

        # Initialize state
        state: AgentState = {
            "agent_id": self.agent_id,
            "current_task": initial_task,
            "status": "thinking",
            "messages": [],
            "thinking_chain": [],
            "tool_calls": [],
            "working_memory": initial_context or {},
            "context": initial_context or {},
            "metadata": {},
        }

        # Execute workflow
        execution_trace = []

        for node_id in self.nodes:
            logger.info(f"Executing node: {node_id}")

            node = self.nodes[node_id]

            try:
                if isinstance(node, ThinkingNode):
                    state = await node.think(state)
                    execution_trace.append(
                        {
                            "node": node_id,
                            "type": "thinking",
                            "status": "completed",
                        }
                    )
                elif isinstance(node, ToolUseNode):
                    # Execute tool with working memory context
                    state, result = await node.execute(state)
                    execution_trace.append(
                        {
                            "node": node_id,
                            "type": "tool",
                            "status": "completed",
                            "result": result,
                        }
                    )
                elif isinstance(node, DecisionNode):
                    state, decision = await node.decide(
                        state,
                        ["continue", "pause", "escalate"],
                    )
                    execution_trace.append(
                        {
                            "node": node_id,
                            "type": "decision",
                            "status": "completed",
                            "decision": decision,
                        }
                    )

            except Exception as e:
                logger.error(f"Node execution failed: {node_id}", exc_info=True)
                execution_trace.append(
                    {
                        "node": node_id,
                        "type": "error",
                        "status": "failed",
                        "error": str(e),
                    }
                )

        state["status"] = "completed"
        state["metadata"]["execution_trace"] = execution_trace

        return state


class AgentPool:
    """Manages a pool of collaborative agents."""

    def __init__(self):
        self.agents: Dict[str, LangGraphAgentBuilder] = {}
        self.collaboration_log: List[Dict[str, Any]] = []

    async def register_agent(
        self, agent_id: str, reasoning_mode: ReasoningMode
    ) -> LangGraphAgentBuilder:
        """Register a new agent."""
        agent = LangGraphAgentBuilder(agent_id, reasoning_mode)
        self.agents[agent_id] = agent
        logger.info(f"Agent registered: {agent_id}")
        return agent

    async def coordinate_agents(
        self,
        task: str,
        agent_ids: List[str],
        orchestration_strategy: str = "sequential",
    ) -> Dict[str, Any]:
        """Coordinate multiple agents."""
        logger.info(f"Coordinating agents: {agent_ids} for task: {task}")

        results = {}

        if orchestration_strategy == "sequential":
            # Execute agents one after another
            context = {}
            for agent_id in agent_ids:
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    result = await agent.build_and_execute(task, context)
                    results[agent_id] = result
                    # Pass result context to next agent
                    context.update(result.get("working_memory", {}))

        elif orchestration_strategy == "parallel":
            # Execute agents concurrently
            import asyncio

            tasks = [
                self.agents[agent_id].build_and_execute(task)
                for agent_id in agent_ids
                if agent_id in self.agents
            ]
            agent_results = await asyncio.gather(*tasks)
            for agent_id, result in zip(agent_ids, agent_results):
                results[agent_id] = result

        # Log collaboration
        self.collaboration_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "task": task,
                "agents": agent_ids,
                "strategy": orchestration_strategy,
                "results": {aid: "completed" for aid in results},
            }
        )

        return {
            "task": task,
            "agents": agent_ids,
            "strategy": orchestration_strategy,
            "results": results,
            "collaboration_log_entry": len(self.collaboration_log),
        }

    def get_collaboration_history(self) -> List[Dict[str, Any]]:
        """Get collaboration history."""
        return self.collaboration_log

    async def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance metrics."""
        if agent_id not in self.agents:
            return {}

        agent = self.agents[agent_id]
        tool_metrics = {}

        for tool_id, tool_node in agent.tools.items():
            tool_metrics[tool_id] = {
                "execution_count": tool_node.execution_count,
                "average_duration_ms": tool_node.average_duration_ms,
            }

        return {
            "agent_id": agent_id,
            "reasoning_mode": agent.reasoning_mode.value,
            "tool_metrics": tool_metrics,
            "memory_size": {
                "short_term": len(agent.memory.short_term),
                "long_term": len(agent.memory.long_term),
                "facts": len(agent.memory.facts),
            },
        }
