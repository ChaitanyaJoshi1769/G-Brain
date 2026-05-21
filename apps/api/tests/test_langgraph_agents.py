"""
Tests for LangGraph-Based Agent Framework
"""

import pytest
from datetime import datetime
from app.services.langgraph_agents import (
    LangGraphAgentBuilder,
    AgentMemory,
    AgentState,
    ThinkingNode,
    ToolUseNode,
    DecisionNode,
    ThinkingStep,
    ReasoningMode,
    AgentPool,
)


@pytest.fixture
def sample_agent_memory():
    """Sample agent memory."""
    return AgentMemory()


@pytest.fixture
def sample_thinking_node():
    """Sample thinking node."""
    return ThinkingNode(ReasoningMode.CHAIN_OF_THOUGHT)


@pytest.fixture
async def sample_tool_fn():
    """Sample tool function."""
    async def mock_tool(**kwargs):
        return {"status": "success", "result": "tool executed"}

    return mock_tool


@pytest.fixture
def sample_agent_state():
    """Sample agent state."""
    return AgentState(
        agent_id="test-agent",
        current_task="test_task",
        status="thinking",
        messages=[],
        thinking_chain=[],
        tool_calls=[],
        working_memory={},
        context={},
        metadata={},
    )


class TestAgentMemory:
    def test_store_short_term(self, sample_agent_memory):
        """Test storing in short-term memory."""
        memory = sample_agent_memory
        memory.store_short_term("key1", "value1")

        assert memory.retrieve_short_term("key1") == "value1"

    def test_store_fact(self, sample_agent_memory):
        """Test storing facts."""
        memory = sample_agent_memory
        memory.store_fact("fact1", "fact_value")

        facts = memory.get_facts()
        assert "fact1" in facts
        assert facts["fact1"] == "fact_value"

    def test_short_term_overflow(self, sample_agent_memory):
        """Test short-term memory overflow to long-term."""
        memory = sample_agent_memory
        memory.max_short_term = 3

        # Add more items than max
        for i in range(5):
            memory.store_short_term(f"key{i}", f"value{i}")

        # Should have promoted some to long-term
        assert len(memory.short_term) <= 3
        assert len(memory.long_term) > 0

    def test_retrieve_nonexistent(self, sample_agent_memory):
        """Test retrieving nonexistent key."""
        memory = sample_agent_memory
        assert memory.retrieve_short_term("nonexistent") is None


class TestThinkingNode:
    @pytest.mark.asyncio
    async def test_think_direct_mode(self, sample_agent_state):
        """Test thinking in direct mode."""
        node = ThinkingNode(ReasoningMode.DIRECT)
        state = sample_agent_state

        result = await node.think(state)

        assert len(result["thinking_chain"]) > 0
        step = result["thinking_chain"][0]
        assert step.step_type == ThinkingStep.ANALYZE

    @pytest.mark.asyncio
    async def test_think_chain_of_thought_mode(self, sample_agent_state):
        """Test thinking in chain of thought mode."""
        node = ThinkingNode(ReasoningMode.CHAIN_OF_THOUGHT)
        state = sample_agent_state

        result = await node.think(state)

        assert len(result["thinking_chain"]) > 0
        assert 0 <= result["thinking_chain"][0].confidence <= 1

    @pytest.mark.asyncio
    async def test_multiple_thinking_steps(self, sample_agent_state):
        """Test multiple thinking steps."""
        node = ThinkingNode(ReasoningMode.REFLECTIVE)
        state = sample_agent_state

        # Multiple thinking iterations
        for _ in range(3):
            state = await node.think(state)

        assert len(state["thinking_chain"]) == 3


class TestToolUseNode:
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, sample_agent_state, sample_tool_fn):
        """Test successful tool execution."""
        node = ToolUseNode("test_tool", sample_tool_fn)
        state = sample_agent_state

        result_state, result = await node.execute(state)

        assert len(result_state["tool_calls"]) > 0
        assert result_state["tool_calls"][0]["status"] == "success"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_tool_with_args(self, sample_agent_state):
        """Test tool execution with arguments."""
        async def parameterized_tool(input_val: str):
            return {"output": f"processed: {input_val}"}

        node = ToolUseNode("param_tool", parameterized_tool)
        state = sample_agent_state

        result_state, result = await node.execute(state, input_val="test_input")

        assert "processed" in result["output"]

    @pytest.mark.asyncio
    async def test_tool_execution_metrics(self, sample_agent_state, sample_tool_fn):
        """Test tool execution metrics tracking."""
        node = ToolUseNode("test_tool", sample_tool_fn)
        state = sample_agent_state

        # Execute multiple times
        for _ in range(3):
            state, _ = await node.execute(state)

        assert node.execution_count == 3
        assert node.average_duration_ms > 0

    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, sample_agent_state):
        """Test tool execution failure handling."""
        async def failing_tool():
            raise ValueError("Tool failed")

        node = ToolUseNode("failing_tool", failing_tool)
        state = sample_agent_state

        result_state, result = await node.execute(state)

        assert result_state["tool_calls"][0]["status"] == "failed"
        assert "error" in result


class TestDecisionNode:
    @pytest.mark.asyncio
    async def test_decide_default(self, sample_agent_state):
        """Test default decision making."""
        node = DecisionNode()
        state = sample_agent_state

        result_state, decision = await node.decide(
            state, ["option_a", "option_b", "option_c"]
        )

        assert decision == "option_a"
        assert len(result_state["messages"]) > 0

    @pytest.mark.asyncio
    async def test_decide_with_custom_fn(self, sample_agent_state):
        """Test decision making with custom function."""
        async def custom_decision_fn(state, options):
            return "option_b"

        node = DecisionNode()
        state = sample_agent_state

        result_state, decision = await node.decide(
            state, ["option_a", "option_b", "option_c"], custom_decision_fn
        )

        assert decision == "option_b"

    @pytest.mark.asyncio
    async def test_decide_empty_options(self, sample_agent_state):
        """Test decision with empty options."""
        node = DecisionNode()
        state = sample_agent_state

        result_state, decision = await node.decide(state, [])

        assert decision == "continue"


class TestLangGraphAgentBuilder:
    @pytest.mark.asyncio
    async def test_build_simple_agent(self, sample_tool_fn):
        """Test building a simple agent."""
        builder = LangGraphAgentBuilder("agent-1", ReasoningMode.DIRECT)

        builder.add_thinking_node("think")
        builder.add_tool_node("execute", "test_tool", sample_tool_fn)
        builder.add_edge("think", "execute")

        assert "think" in builder.nodes
        assert "execute" in builder.nodes
        assert ("think", "execute") in builder.edges

    @pytest.mark.asyncio
    async def test_build_and_execute_workflow(self, sample_tool_fn):
        """Test building and executing a workflow."""
        builder = LangGraphAgentBuilder("agent-1", ReasoningMode.CHAIN_OF_THOUGHT)

        builder.add_thinking_node("think")
        builder.add_tool_node("execute", "tool1", sample_tool_fn)
        builder.add_decision_node("decide")
        builder.add_edge("think", "execute")
        builder.add_edge("execute", "decide")

        result = await builder.build_and_execute(
            "test_task", {"context_key": "context_value"}
        )

        assert result["agent_id"] == "agent-1"
        assert result["status"] == "completed"
        assert len(result["thinking_chain"]) > 0
        assert len(result["tool_calls"]) > 0

    @pytest.mark.asyncio
    async def test_agent_memory_integration(self, sample_tool_fn):
        """Test agent memory integration."""
        builder = LangGraphAgentBuilder("agent-1", ReasoningMode.DIRECT)

        builder.add_thinking_node("think")
        builder.memory.store_short_term("context", {"key": "value"})
        builder.memory.store_fact("learned_fact", "fact_value")

        result = await builder.build_and_execute("test_task")

        assert len(builder.memory.short_term) > 0
        facts = builder.memory.get_facts()
        assert "learned_fact" in facts

    @pytest.mark.asyncio
    async def test_multiple_tool_execution(self, sample_tool_fn):
        """Test executing multiple tools."""
        builder = LangGraphAgentBuilder("agent-1", ReasoningMode.CHAIN_OF_THOUGHT)

        builder.add_tool_node("tool1", "tool1", sample_tool_fn)
        builder.add_tool_node("tool2", "tool2", sample_tool_fn)
        builder.add_edge("tool1", "tool2")

        result = await builder.build_and_execute("test_task")

        assert len(result["tool_calls"]) >= 2


class TestAgentPool:
    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test agent registration."""
        pool = AgentPool()

        agent = await pool.register_agent("agent-1", ReasoningMode.DIRECT)

        assert "agent-1" in pool.agents
        assert pool.agents["agent-1"] == agent

    @pytest.mark.asyncio
    async def test_sequential_coordination(self, sample_tool_fn):
        """Test sequential agent coordination."""
        pool = AgentPool()

        agent1 = await pool.register_agent("agent-1", ReasoningMode.DIRECT)
        agent1.add_thinking_node("think1")
        agent1.add_tool_node("tool1", "tool1", sample_tool_fn)

        agent2 = await pool.register_agent("agent-2", ReasoningMode.CHAIN_OF_THOUGHT)
        agent2.add_thinking_node("think2")

        result = await pool.coordinate_agents(
            "test_task", ["agent-1", "agent-2"], "sequential"
        )

        assert result["strategy"] == "sequential"
        assert "agent-1" in result["results"]
        assert "agent-2" in result["results"]

    @pytest.mark.asyncio
    async def test_parallel_coordination(self, sample_tool_fn):
        """Test parallel agent coordination."""
        pool = AgentPool()

        for i in range(3):
            agent = await pool.register_agent(f"agent-{i}", ReasoningMode.DIRECT)
            agent.add_thinking_node(f"think{i}")

        result = await pool.coordinate_agents(
            "test_task", ["agent-0", "agent-1", "agent-2"], "parallel"
        )

        assert result["strategy"] == "parallel"
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_collaboration_history(self, sample_tool_fn):
        """Test collaboration history tracking."""
        pool = AgentPool()

        agent = await pool.register_agent("agent-1", ReasoningMode.DIRECT)
        agent.add_thinking_node("think")

        await pool.coordinate_agents("task1", ["agent-1"], "sequential")
        await pool.coordinate_agents("task2", ["agent-1"], "sequential")

        history = pool.get_collaboration_history()
        assert len(history) == 2
        assert history[0]["task"] == "task1"
        assert history[1]["task"] == "task2"

    @pytest.mark.asyncio
    async def test_agent_metrics(self, sample_tool_fn):
        """Test agent metrics collection."""
        pool = AgentPool()

        agent = await pool.register_agent("agent-1", ReasoningMode.DIRECT)
        agent.add_tool_node("tool1", "tool1", sample_tool_fn)

        await agent.build_and_execute("test_task")

        metrics = await pool.get_agent_metrics("agent-1")

        assert metrics["agent_id"] == "agent-1"
        assert "tool_metrics" in metrics
        assert "memory_size" in metrics


@pytest.mark.asyncio
async def test_end_to_end_agent_workflow():
    """Test end-to-end agent workflow."""
    async def query_tool(**kwargs):
        return {"data": "query_result"}

    async def analyze_tool(**kwargs):
        return {"analysis": "analysis_result"}

    builder = LangGraphAgentBuilder("analyst-1", ReasoningMode.CHAIN_OF_THOUGHT)

    builder.add_thinking_node("plan")
    builder.add_tool_node("query", "query_knowledge", query_tool)
    builder.add_tool_node("analyze", "analyze_results", analyze_tool)
    builder.add_decision_node("decide")

    builder.add_edge("plan", "query")
    builder.add_edge("query", "analyze")
    builder.add_edge("analyze", "decide")

    result = await builder.build_and_execute(
        "analyze_customer_data", {"customer_id": "cust-123"}
    )

    assert result["status"] == "completed"
    assert len(result["thinking_chain"]) > 0
    assert len(result["tool_calls"]) >= 2
    assert result["working_memory"]["customer_id"] == "cust-123"


@pytest.mark.asyncio
async def test_multi_agent_collaboration():
    """Test multi-agent collaboration."""
    pool = AgentPool()

    async def research_tool(**kwargs):
        return {"research": "findings"}

    async def implement_tool(**kwargs):
        return {"implementation": "complete"}

    # Research agent
    researcher = await pool.register_agent("researcher", ReasoningMode.CHAIN_OF_THOUGHT)
    researcher.add_thinking_node("research_plan")
    researcher.add_tool_node("research", "research_knowledge", research_tool)

    # Implementation agent
    implementer = await pool.register_agent("implementer", ReasoningMode.DIRECT)
    implementer.add_tool_node("implement", "implement_solution", implement_tool)

    # Coordinate agents
    result = await pool.coordinate_agents(
        "complete_project", ["researcher", "implementer"], "sequential"
    )

    assert len(result["results"]) == 2
    assert "researcher" in result["results"]
    assert "implementer" in result["results"]

    # Verify context was passed between agents
    researcher_result = result["results"]["researcher"]
    assert researcher_result["status"] == "completed"
