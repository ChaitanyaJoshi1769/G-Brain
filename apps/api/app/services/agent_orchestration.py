"""
Agent Orchestration Engine

Coordinates multi-agent workflows using LangGraph for autonomous intelligence execution.
Implements safety guardrails, approval workflows, and tool management.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent roles in the system."""
    ANALYST = "analyst"  # Data analysis and research
    EXECUTOR = "executor"  # Execute tasks and workflows
    APPROVER = "approver"  # Review and approve actions
    MONITOR = "monitor"  # Monitor and alert
    COORDINATOR = "coordinator"  # Orchestrate multi-agent workflows


class ExecutionStatus(str, Enum):
    """Status of agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class SafetyLevel(str, Enum):
    """Safety levels for actions."""
    LOW = "low"  # No approval needed
    MEDIUM = "medium"  # Manager approval needed
    HIGH = "high"  # Multi-level approval needed
    CRITICAL = "critical"  # Requires executive approval


@dataclass
class AgentCapability:
    """Capability that an agent has."""
    name: str
    description: str
    required_tools: List[str] = field(default_factory=list)
    supported_domains: List[str] = field(default_factory=list)
    max_concurrent_executions: int = 5


@dataclass
class Tool:
    """Tool available to agents."""
    id: str
    name: str
    description: str
    category: str  # "query", "action", "approval", "integration"
    parameters: Dict[str, Any]
    requires_approval: bool = False
    safety_level: SafetyLevel = SafetyLevel.LOW
    available_to_roles: List[AgentRole] = field(default_factory=list)


@dataclass
class AgentAction:
    """Action taken by an agent."""
    id: str
    agent_id: str
    action_type: str  # "execute_skill", "query_knowledge", "request_approval", etc.
    description: str
    parameters: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    safety_level: SafetyLevel = SafetyLevel.LOW
    requires_approval: bool = False
    approval_chain: List[str] = field(default_factory=list)  # Approvers


@dataclass
class Agent:
    """Agent definition."""
    id: str
    name: str
    role: AgentRole
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 300
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "required_tools": c.required_tools,
                }
                for c in self.capabilities
            ],
            "available_tools": self.available_tools,
            "is_active": self.is_active,
        }


@dataclass
class WorkflowStep:
    """Step in a multi-agent workflow."""
    id: str
    agent_id: str
    action: AgentAction
    depends_on: List[str] = field(default_factory=list)  # Step IDs
    parallel_with: List[str] = field(default_factory=list)  # Can run in parallel
    success_criteria: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class ExecutionContext:
    """Context for an agent execution."""
    execution_id: str
    workflow_id: str
    agent: Agent
    step: WorkflowStep
    current_step: int
    total_steps: int
    previous_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApprovalRequest:
    """Request for approval of an action."""
    id: str
    action_id: str
    agent_id: str
    requested_by: str
    description: str
    details: Dict[str, Any]
    required_approvers: List[str]
    approval_level: SafetyLevel
    requested_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected


@dataclass
class ExecutionResult:
    """Result of agent execution."""
    execution_id: str
    workflow_id: str
    agent_id: str
    status: ExecutionStatus
    output: Dict[str, Any]
    duration_seconds: float
    actions_executed: List[AgentAction]
    approvals_required: List[ApprovalRequest]
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "output": self.output,
            "duration_seconds": self.duration_seconds,
            "actions_executed": len(self.actions_executed),
            "approvals_required": len(self.approvals_required),
            "errors": self.errors,
        }


class ToolRegistry:
    """Manages available tools for agents."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    async def register_tool(self, tool: Tool) -> None:
        """Register a new tool."""
        logger.info(f"Registering tool: {tool.name}")
        self.tools[tool.id] = tool

    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID."""
        return self.tools.get(tool_id)

    async def list_tools(
        self, role: Optional[AgentRole] = None, category: Optional[str] = None
    ) -> List[Tool]:
        """List available tools."""
        tools = list(self.tools.values())

        if role:
            tools = [t for t in tools if role in t.available_to_roles]

        if category:
            tools = [t for t in tools if t.category == category]

        return tools

    async def validate_tool_access(self, agent: Agent, tool_id: str) -> bool:
        """Check if agent can use tool."""
        if tool_id not in agent.available_tools:
            return False

        tool = await self.get_tool(tool_id)
        if not tool:
            return False

        return agent.role in tool.available_to_roles


class ApprovalManager:
    """Manages approval workflows."""

    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []

    async def request_approval(self, request: ApprovalRequest) -> str:
        """Request approval for an action."""
        logger.info(f"Approval requested: {request.id} for action {request.action_id}")
        self.pending_approvals[request.id] = request
        return request.id

    async def approve(
        self, approval_id: str, approved_by: str, notes: Optional[str] = None
    ) -> bool:
        """Approve a request."""
        if approval_id not in self.pending_approvals:
            return False

        request = self.pending_approvals[approval_id]
        request.status = "approved"
        request.approved_by = approved_by
        request.approved_at = datetime.utcnow()

        del self.pending_approvals[approval_id]
        self.approval_history.append(request)

        logger.info(f"Approval granted: {approval_id}")
        return True

    async def reject(
        self, approval_id: str, rejected_by: str, reason: str
    ) -> bool:
        """Reject a request."""
        if approval_id not in self.pending_approvals:
            return False

        request = self.pending_approvals[approval_id]
        request.status = "rejected"
        request.approved_by = rejected_by
        request.approved_at = datetime.utcnow()

        del self.pending_approvals[approval_id]
        self.approval_history.append(request)

        logger.info(f"Approval rejected: {approval_id}")
        return True

    async def get_pending_approvals(
        self, approver: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending approvals."""
        approvals = list(self.pending_approvals.values())

        if approver:
            approvals = [a for a in approvals if approver in a.required_approvers]

        return approvals


class AgentFactory:
    """Creates and manages agents."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.agents: Dict[str, Agent] = {}

    async def create_agent(
        self,
        name: str,
        role: AgentRole,
        description: str,
        capabilities: List[AgentCapability],
        available_tools: List[str],
    ) -> Agent:
        """Create a new agent."""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            description=description,
            capabilities=capabilities,
            available_tools=available_tools,
        )

        self.agents[agent_id] = agent
        logger.info(f"Agent created: {name} ({agent_id})")
        return agent

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    async def list_agents(self, role: Optional[AgentRole] = None) -> List[Agent]:
        """List agents."""
        agents = list(self.agents.values())

        if role:
            agents = [a for a in agents if a.role == role]

        return agents

    async def deactivate_agent(self, agent_id: str) -> bool:
        """Deactivate an agent."""
        if agent_id not in self.agents:
            return False

        self.agents[agent_id].is_active = False
        logger.info(f"Agent deactivated: {agent_id}")
        return True


class ExecutionEngine:
    """Executes agent actions."""

    def __init__(self, approval_manager: ApprovalManager):
        self.approval_manager = approval_manager
        self.executions: Dict[str, ExecutionResult] = {}

    async def execute_action(
        self,
        agent: Agent,
        action: AgentAction,
        context: ExecutionContext,
    ) -> Tuple[ExecutionStatus, Dict[str, Any]]:
        """Execute an agent action."""
        logger.info(f"Executing action: {action.id} by agent {agent.id}")

        action.status = ExecutionStatus.RUNNING

        # Check if approval is needed
        if action.requires_approval or action.safety_level in [
            SafetyLevel.HIGH,
            SafetyLevel.CRITICAL,
        ]:
            approval_req = ApprovalRequest(
                id=f"approval-{uuid.uuid4().hex[:8]}",
                action_id=action.id,
                agent_id=agent.id,
                requested_by=agent.id,
                description=action.description,
                details=action.parameters,
                required_approvers=action.approval_chain,
                approval_level=action.safety_level,
            )

            approval_id = await self.approval_manager.request_approval(approval_req)
            action.status = ExecutionStatus.WAITING_APPROVAL

            return ExecutionStatus.WAITING_APPROVAL, {"approval_id": approval_id}

        # Execute action (mock implementation)
        try:
            # TODO: Integrate with actual execution logic
            result = await self._execute_action_impl(action, context)
            action.status = ExecutionStatus.COMPLETED
            action.result = result
            return ExecutionStatus.COMPLETED, result
        except Exception as e:
            action.status = ExecutionStatus.FAILED
            action.error = str(e)
            logger.error(f"Action execution failed: {action.id}", exc_info=True)
            return ExecutionStatus.FAILED, {"error": str(e)}

    async def _execute_action_impl(
        self, action: AgentAction, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Implementation of action execution."""
        # Mock execution - return success response
        return {
            "action_id": action.id,
            "status": "executed",
            "result": f"Executed {action.action_type}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def execute_workflow(
        self, workflow_id: str, steps: List[WorkflowStep], agents: Dict[str, Agent]
    ) -> ExecutionResult:
        """Execute a multi-step workflow."""
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()

        logger.info(f"Starting workflow execution: {workflow_id}")

        actions_executed = []
        approvals_required = []
        errors = []

        for step in steps:
            agent = agents.get(step.agent_id)
            if not agent:
                errors.append(f"Agent not found: {step.agent_id}")
                continue

            context = ExecutionContext(
                execution_id=execution_id,
                workflow_id=workflow_id,
                agent=agent,
                step=step,
                current_step=steps.index(step),
                total_steps=len(steps),
            )

            status, result = await self.execute_action(agent, step.action, context)
            actions_executed.append(step.action)

            if status == ExecutionStatus.WAITING_APPROVAL:
                approvals_required.append(
                    ApprovalRequest(
                        id=result.get("approval_id", "unknown"),
                        action_id=step.action.id,
                        agent_id=agent.id,
                        requested_by=agent.id,
                        description=step.action.description,
                        details=step.action.parameters,
                        required_approvers=step.action.approval_chain,
                        approval_level=step.action.safety_level,
                    )
                )

            if status == ExecutionStatus.FAILED:
                errors.append(f"Step failed: {step.id}")

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow_id,
            agent_id="orchestrator",
            status=ExecutionStatus.COMPLETED
            if not errors
            else ExecutionStatus.FAILED,
            output={"actions": [a.id for a in actions_executed]},
            duration_seconds=duration,
            actions_executed=actions_executed,
            approvals_required=approvals_required,
            errors=errors,
        )

        self.executions[execution_id] = result
        logger.info(f"Workflow execution completed: {execution_id}")
        return result


class AgentOrchestrator:
    """Main agent orchestration engine."""

    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.approval_manager = ApprovalManager()
        self.agent_factory = AgentFactory(self.tool_registry)
        self.execution_engine = ExecutionEngine(self.approval_manager)
        self.workflows: Dict[str, List[WorkflowStep]] = {}

    async def register_tool(
        self,
        name: str,
        description: str,
        category: str,
        parameters: Dict[str, Any],
        requires_approval: bool = False,
        safety_level: SafetyLevel = SafetyLevel.LOW,
        available_to_roles: Optional[List[AgentRole]] = None,
    ) -> Tool:
        """Register a new tool."""
        tool = Tool(
            id=f"tool-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            requires_approval=requires_approval,
            safety_level=safety_level,
            available_to_roles=available_to_roles or [],
        )

        await self.tool_registry.register_tool(tool)
        return tool

    async def create_agent(
        self,
        name: str,
        role: AgentRole,
        description: str,
        capabilities: List[AgentCapability],
        available_tools: List[str],
    ) -> Agent:
        """Create a new agent."""
        return await self.agent_factory.create_agent(
            name, role, description, capabilities, available_tools
        )

    async def create_workflow(
        self, workflow_id: str, steps: List[WorkflowStep]
    ) -> None:
        """Register a workflow."""
        logger.info(f"Registering workflow: {workflow_id}")
        self.workflows[workflow_id] = steps

    async def execute_workflow(self, workflow_id: str) -> ExecutionResult:
        """Execute a registered workflow."""
        steps = self.workflows.get(workflow_id)
        if not steps:
            raise ValueError(f"Workflow not found: {workflow_id}")

        agents = {}
        for step in steps:
            agent = await self.agent_factory.get_agent(step.agent_id)
            if agent:
                agents[step.agent_id] = agent

        return await self.execution_engine.execute_workflow(workflow_id, steps, agents)

    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution status."""
        return self.execution_engine.executions.get(execution_id)

    async def request_approval(
        self,
        action_id: str,
        agent_id: str,
        description: str,
        required_approvers: List[str],
        safety_level: SafetyLevel,
    ) -> str:
        """Request approval for an action."""
        request = ApprovalRequest(
            id=f"approval-{uuid.uuid4().hex[:8]}",
            action_id=action_id,
            agent_id=agent_id,
            requested_by=agent_id,
            description=description,
            details={},
            required_approvers=required_approvers,
            approval_level=safety_level,
        )

        return await self.approval_manager.request_approval(request)

    async def approve_action(
        self, approval_id: str, approved_by: str
    ) -> bool:
        """Approve an action."""
        return await self.approval_manager.approve(approval_id, approved_by)

    async def reject_action(
        self, approval_id: str, rejected_by: str, reason: str
    ) -> bool:
        """Reject an action."""
        return await self.approval_manager.reject(approval_id, rejected_by, reason)

    async def get_pending_approvals(
        self, approver: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending approvals."""
        return await self.approval_manager.get_pending_approvals(approver)
