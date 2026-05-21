"""
Tests for Agent Orchestration Engine
"""

import pytest
from datetime import datetime
from app.services.agent_orchestration import (
    AgentOrchestrator,
    AgentRole,
    SafetyLevel,
    ExecutionStatus,
    Agent,
    AgentCapability,
    Tool,
    AgentAction,
    WorkflowStep,
    ApprovalRequest,
    ExecutionContext,
    ExecutionResult,
    ToolRegistry,
    ApprovalManager,
    AgentFactory,
    ExecutionEngine,
)


@pytest.fixture
def sample_tools():
    """Sample tools for testing."""
    return [
        Tool(
            id="tool-query",
            name="Query Knowledge",
            description="Query the knowledge base",
            category="query",
            parameters={"query": {"type": "string"}},
            available_to_roles=[AgentRole.ANALYST],
        ),
        Tool(
            id="tool-execute",
            name="Execute Skill",
            description="Execute a skill",
            category="action",
            parameters={"skill_id": {"type": "string"}},
            requires_approval=True,
            safety_level=SafetyLevel.MEDIUM,
            available_to_roles=[AgentRole.EXECUTOR],
        ),
        Tool(
            id="tool-approve",
            name="Approve Action",
            description="Approve an action",
            category="approval",
            parameters={"action_id": {"type": "string"}},
            available_to_roles=[AgentRole.APPROVER],
        ),
    ]


@pytest.fixture
def sample_agents():
    """Sample agents for testing."""
    return [
        Agent(
            id="agent-analyst",
            name="Data Analyst",
            role=AgentRole.ANALYST,
            description="Analyzes data and finds patterns",
            available_tools=["tool-query"],
        ),
        Agent(
            id="agent-executor",
            name="Task Executor",
            role=AgentRole.EXECUTOR,
            description="Executes tasks and workflows",
            available_tools=["tool-execute"],
        ),
        Agent(
            id="agent-approver",
            name="Approval Agent",
            role=AgentRole.APPROVER,
            description="Approves high-level actions",
            available_tools=["tool-approve"],
        ),
    ]


class TestAgent:
    def test_agent_creation(self):
        """Test agent creation."""
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test description",
            available_tools=["tool-1", "tool-2"],
        )

        assert agent.id == "agent-1"
        assert agent.role == AgentRole.EXECUTOR
        assert len(agent.available_tools) == 2

    def test_agent_to_dict(self):
        """Test agent serialization."""
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test description",
            available_tools=["tool-1"],
            capabilities=[
                AgentCapability(
                    name="test_capability",
                    description="A test capability",
                )
            ],
        )

        result = agent.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "agent-1"
        assert result["role"] == "executor"


class TestToolRegistry:
    @pytest.mark.asyncio
    async def test_register_tool(self, sample_tools):
        """Test tool registration."""
        registry = ToolRegistry()

        await registry.register_tool(sample_tools[0])

        tool = await registry.get_tool(sample_tools[0].id)
        assert tool is not None
        assert tool.name == sample_tools[0].name

    @pytest.mark.asyncio
    async def test_list_tools(self, sample_tools):
        """Test listing tools."""
        registry = ToolRegistry()

        for tool in sample_tools:
            await registry.register_tool(tool)

        all_tools = await registry.list_tools()
        assert len(all_tools) == len(sample_tools)

    @pytest.mark.asyncio
    async def test_list_tools_by_role(self, sample_tools):
        """Test filtering tools by role."""
        registry = ToolRegistry()

        for tool in sample_tools:
            await registry.register_tool(tool)

        analyst_tools = await registry.list_tools(role=AgentRole.ANALYST)
        assert len(analyst_tools) > 0
        assert all(AgentRole.ANALYST in t.available_to_roles for t in analyst_tools)

    @pytest.mark.asyncio
    async def test_validate_tool_access(self, sample_tools, sample_agents):
        """Test tool access validation."""
        registry = ToolRegistry()

        for tool in sample_tools:
            await registry.register_tool(tool)

        # Analyst can use query tool
        can_access = await registry.validate_tool_access(
            sample_agents[0], "tool-query"
        )
        assert can_access is True

        # Analyst cannot use execute tool
        can_access = await registry.validate_tool_access(
            sample_agents[0], "tool-execute"
        )
        assert can_access is False


class TestApprovalManager:
    @pytest.mark.asyncio
    async def test_request_approval(self):
        """Test approval request."""
        manager = ApprovalManager()

        request = ApprovalRequest(
            id="approval-1",
            action_id="action-1",
            agent_id="agent-1",
            requested_by="agent-1",
            description="Test approval",
            details={},
            required_approvers=["approver-1"],
            approval_level=SafetyLevel.MEDIUM,
        )

        approval_id = await manager.request_approval(request)

        assert approval_id == "approval-1"
        assert approval_id in manager.pending_approvals

    @pytest.mark.asyncio
    async def test_approve(self):
        """Test approval."""
        manager = ApprovalManager()

        request = ApprovalRequest(
            id="approval-1",
            action_id="action-1",
            agent_id="agent-1",
            requested_by="agent-1",
            description="Test approval",
            details={},
            required_approvers=["approver-1"],
            approval_level=SafetyLevel.MEDIUM,
        )

        await manager.request_approval(request)
        result = await manager.approve("approval-1", "approver-1")

        assert result is True
        assert "approval-1" not in manager.pending_approvals
        assert len(manager.approval_history) == 1

    @pytest.mark.asyncio
    async def test_reject(self):
        """Test rejection."""
        manager = ApprovalManager()

        request = ApprovalRequest(
            id="approval-1",
            action_id="action-1",
            agent_id="agent-1",
            requested_by="agent-1",
            description="Test approval",
            details={},
            required_approvers=["approver-1"],
            approval_level=SafetyLevel.MEDIUM,
        )

        await manager.request_approval(request)
        result = await manager.reject("approval-1", "approver-1", "Not needed")

        assert result is True
        assert "approval-1" not in manager.pending_approvals

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self):
        """Test getting pending approvals."""
        manager = ApprovalManager()

        request1 = ApprovalRequest(
            id="approval-1",
            action_id="action-1",
            agent_id="agent-1",
            requested_by="agent-1",
            description="Test approval 1",
            details={},
            required_approvers=["approver-1"],
            approval_level=SafetyLevel.MEDIUM,
        )

        request2 = ApprovalRequest(
            id="approval-2",
            action_id="action-2",
            agent_id="agent-2",
            requested_by="agent-2",
            description="Test approval 2",
            details={},
            required_approvers=["approver-2"],
            approval_level=SafetyLevel.HIGH,
        )

        await manager.request_approval(request1)
        await manager.request_approval(request2)

        pending = await manager.get_pending_approvals()
        assert len(pending) == 2

        pending_for_approver1 = await manager.get_pending_approvals("approver-1")
        assert len(pending_for_approver1) == 1


class TestAgentFactory:
    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Test agent creation."""
        registry = ToolRegistry()
        factory = AgentFactory(registry)

        agent = await factory.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test description",
            capabilities=[],
            available_tools=["tool-1"],
        )

        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.role == AgentRole.EXECUTOR

    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Test listing agents."""
        registry = ToolRegistry()
        factory = AgentFactory(registry)

        agent1 = await factory.create_agent(
            name="Agent 1",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        agent2 = await factory.create_agent(
            name="Agent 2",
            role=AgentRole.ANALYST,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        all_agents = await factory.list_agents()
        assert len(all_agents) == 2

        executor_agents = await factory.list_agents(AgentRole.EXECUTOR)
        assert len(executor_agents) == 1

    @pytest.mark.asyncio
    async def test_deactivate_agent(self):
        """Test agent deactivation."""
        registry = ToolRegistry()
        factory = AgentFactory(registry)

        agent = await factory.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        result = await factory.deactivate_agent(agent.id)
        assert result is True

        deactivated = await factory.get_agent(agent.id)
        assert deactivated.is_active is False


class TestExecutionEngine:
    @pytest.mark.asyncio
    async def test_execute_action_no_approval(self):
        """Test action execution without approval."""
        manager = ApprovalManager()
        engine = ExecutionEngine(manager)

        agent = Agent(
            id="agent-1",
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
        )

        action = AgentAction(
            id="action-1",
            agent_id="agent-1",
            action_type="execute_skill",
            description="Test action",
            parameters={},
            requires_approval=False,
            safety_level=SafetyLevel.LOW,
        )

        context = ExecutionContext(
            execution_id="exec-1",
            workflow_id="workflow-1",
            agent=agent,
            step=WorkflowStep(
                id="step-1",
                agent_id="agent-1",
                action=action,
            ),
            current_step=0,
            total_steps=1,
        )

        status, result = await engine.execute_action(agent, action, context)

        assert status == ExecutionStatus.COMPLETED
        assert "action_id" in result

    @pytest.mark.asyncio
    async def test_execute_action_with_approval(self):
        """Test action execution with approval."""
        manager = ApprovalManager()
        engine = ExecutionEngine(manager)

        agent = Agent(
            id="agent-1",
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
        )

        action = AgentAction(
            id="action-1",
            agent_id="agent-1",
            action_type="execute_skill",
            description="Test action",
            parameters={},
            requires_approval=True,
            safety_level=SafetyLevel.MEDIUM,
            approval_chain=["approver-1"],
        )

        context = ExecutionContext(
            execution_id="exec-1",
            workflow_id="workflow-1",
            agent=agent,
            step=WorkflowStep(
                id="step-1",
                agent_id="agent-1",
                action=action,
            ),
            current_step=0,
            total_steps=1,
        )

        status, result = await engine.execute_action(agent, action, context)

        assert status == ExecutionStatus.WAITING_APPROVAL
        assert "approval_id" in result

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test workflow execution."""
        manager = ApprovalManager()
        engine = ExecutionEngine(manager)

        agent = Agent(
            id="agent-1",
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
        )

        action = AgentAction(
            id="action-1",
            agent_id="agent-1",
            action_type="execute_skill",
            description="Test action",
            parameters={},
        )

        step = WorkflowStep(
            id="step-1",
            agent_id="agent-1",
            action=action,
        )

        result = await engine.execute_workflow(
            "workflow-1",
            [step],
            {"agent-1": agent},
        )

        assert isinstance(result, ExecutionResult)
        assert result.workflow_id == "workflow-1"


class TestAgentOrchestrator:
    @pytest.mark.asyncio
    async def test_register_tool(self):
        """Test tool registration."""
        orchestrator = AgentOrchestrator()

        tool = await orchestrator.register_tool(
            name="Test Tool",
            description="Test description",
            category="query",
            parameters={"query": {"type": "string"}},
        )

        assert tool.id is not None
        assert tool.name == "Test Tool"

    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Test agent creation."""
        orchestrator = AgentOrchestrator()

        agent = await orchestrator.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        assert agent.id is not None
        assert agent.name == "Test Agent"

    @pytest.mark.asyncio
    async def test_create_workflow(self):
        """Test workflow creation."""
        orchestrator = AgentOrchestrator()

        agent = await orchestrator.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        action = AgentAction(
            id="action-1",
            agent_id=agent.id,
            action_type="execute_skill",
            description="Test",
            parameters={},
        )

        step = WorkflowStep(
            id="step-1",
            agent_id=agent.id,
            action=action,
        )

        await orchestrator.create_workflow("workflow-1", [step])

        assert "workflow-1" in orchestrator.workflows

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test workflow execution."""
        orchestrator = AgentOrchestrator()

        agent = await orchestrator.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        action = AgentAction(
            id="action-1",
            agent_id=agent.id,
            action_type="execute_skill",
            description="Test",
            parameters={},
        )

        step = WorkflowStep(
            id="step-1",
            agent_id=agent.id,
            action=action,
        )

        await orchestrator.create_workflow("workflow-1", [step])
        result = await orchestrator.execute_workflow("workflow-1")

        assert result.workflow_id == "workflow-1"
        assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

    @pytest.mark.asyncio
    async def test_approval_workflow(self):
        """Test approval workflow."""
        orchestrator = AgentOrchestrator()

        # Create agent
        agent = await orchestrator.create_agent(
            name="Test Agent",
            role=AgentRole.EXECUTOR,
            description="Test",
            capabilities=[],
            available_tools=[],
        )

        # Request approval
        approval_id = await orchestrator.request_approval(
            action_id="action-1",
            agent_id=agent.id,
            description="Test approval",
            required_approvers=["approver-1"],
            safety_level=SafetyLevel.MEDIUM,
        )

        assert approval_id is not None

        # Check pending approvals
        pending = await orchestrator.get_pending_approvals()
        assert len(pending) > 0

        # Approve
        result = await orchestrator.approve_action(approval_id, "approver-1")
        assert result is True

        # Check no more pending
        pending = await orchestrator.get_pending_approvals()
        assert len(pending) == 0


@pytest.mark.asyncio
async def test_end_to_end_multi_agent_workflow():
    """Test end-to-end multi-agent workflow."""
    orchestrator = AgentOrchestrator()

    # Create agents
    analyst = await orchestrator.create_agent(
        name="Analyst",
        role=AgentRole.ANALYST,
        description="Analyzes data",
        capabilities=[],
        available_tools=["tool-query"],
    )

    executor = await orchestrator.create_agent(
        name="Executor",
        role=AgentRole.EXECUTOR,
        description="Executes tasks",
        capabilities=[],
        available_tools=["tool-execute"],
    )

    approver = await orchestrator.create_agent(
        name="Approver",
        role=AgentRole.APPROVER,
        description="Approves actions",
        capabilities=[],
        available_tools=["tool-approve"],
    )

    # Create workflow with multiple steps
    steps = [
        WorkflowStep(
            id="step-1",
            agent_id=analyst.id,
            action=AgentAction(
                id="action-1",
                agent_id=analyst.id,
                action_type="query_knowledge",
                description="Query knowledge base",
                parameters={"query": "test"},
            ),
        ),
        WorkflowStep(
            id="step-2",
            agent_id=executor.id,
            action=AgentAction(
                id="action-2",
                agent_id=executor.id,
                action_type="execute_skill",
                description="Execute skill",
                parameters={"skill_id": "skill-1"},
                requires_approval=True,
                safety_level=SafetyLevel.MEDIUM,
                approval_chain=[approver.id],
            ),
            depends_on=["step-1"],
        ),
    ]

    await orchestrator.create_workflow("workflow-1", steps)
    result = await orchestrator.execute_workflow("workflow-1")

    assert result is not None
    assert len(result.actions_executed) > 0
