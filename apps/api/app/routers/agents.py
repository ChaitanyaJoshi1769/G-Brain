"""
Agent Orchestration Endpoints

Provides endpoints for creating, managing, and executing autonomous agents.
Implements multi-agent workflows with safety guardrails and approval workflows.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.agent_orchestration import (
    AgentOrchestrator,
    AgentRole,
    SafetyLevel,
    Agent,
    AgentCapability,
    AgentAction,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global orchestrator instance
orchestrator = AgentOrchestrator()


class AgentRequest(BaseModel):
    """Agent creation request."""
    name: str
    role: str
    description: str
    available_tools: List[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Agent response."""
    id: str
    name: str
    role: str
    description: str
    available_tools: List[str]
    is_active: bool


class ToolRequest(BaseModel):
    """Tool registration request."""
    name: str
    description: str
    category: str
    parameters: dict
    requires_approval: bool = False
    safety_level: str = "low"


class WorkflowStepRequest(BaseModel):
    """Workflow step definition."""
    agent_id: str
    action_type: str
    description: str
    parameters: dict
    safety_level: str = "low"
    requires_approval: bool = False
    approval_chain: List[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    """Workflow execution request."""
    workflow_id: str
    steps: List[WorkflowStepRequest]


class ApprovalRequest(BaseModel):
    """Approval request."""
    action_id: str
    description: str
    required_approvers: List[str]
    safety_level: str = "medium"


class ApprovalResponseRequest(BaseModel):
    """Approval response (approve/reject)."""
    approval_id: str
    approved_by: str
    action: str  # "approve" or "reject"
    reason: Optional[str] = None


@router.post("")
async def create_agent(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """
    Create a new agent.

    Args:
        request: Agent creation request
        db: Database session

    Returns:
        Created agent
    """
    logger.info(f"Creating agent: {request.name}")

    try:
        # Parse role
        role = AgentRole(request.role)

        # Create default capabilities
        capabilities = [
            AgentCapability(
                name="task_execution",
                description="Execute tasks and workflows",
                required_tools=request.available_tools,
            )
        ]

        # Create agent
        agent = await orchestrator.create_agent(
            name=request.name,
            role=role,
            description=request.description,
            capabilities=capabilities,
            available_tools=request.available_tools,
        )

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            role=agent.role.value,
            description=agent.description,
            available_tools=agent.available_tools,
            is_active=agent.is_active,
        )

    except Exception as e:
        logger.error(f"Agent creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent creation failed: {str(e)}",
        )


@router.get("")
async def list_agents(
    role: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    List agents.

    Args:
        role: Filter by role
        db: Database session

    Returns:
        List of agents
    """
    logger.info(f"Listing agents (role={role})")

    try:
        agent_role = None
        if role:
            agent_role = AgentRole(role)

        agents = await orchestrator.agent_factory.list_agents(agent_role)

        return {
            "total": len(agents),
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role.value,
                    "description": a.description,
                    "is_active": a.is_active,
                }
                for a in agents
            ],
        }

    except Exception as e:
        logger.error(f"Listing agents failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Listing agents failed: {str(e)}",
        )


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get agent by ID.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Agent details
    """
    logger.info(f"Getting agent: {agent_id}")

    try:
        agent = await orchestrator.agent_factory.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        return agent.to_dict()

    except Exception as e:
        logger.error(f"Getting agent failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting agent failed: {str(e)}",
        )


@router.post("/tools/register")
async def register_tool(
    request: ToolRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Register a new tool.

    Args:
        request: Tool registration request
        db: Database session

    Returns:
        Registered tool
    """
    logger.info(f"Registering tool: {request.name}")

    try:
        safety_level = SafetyLevel(request.safety_level)

        tool = await orchestrator.register_tool(
            name=request.name,
            description=request.description,
            category=request.category,
            parameters=request.parameters,
            requires_approval=request.requires_approval,
            safety_level=safety_level,
        )

        return {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "safety_level": tool.safety_level.value,
        }

    except Exception as e:
        logger.error(f"Tool registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool registration failed: {str(e)}",
        )


@router.post("/workflows")
async def create_workflow(
    request: WorkflowRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Create and register a workflow.

    Args:
        request: Workflow request
        db: Database session

    Returns:
        Workflow confirmation
    """
    logger.info(f"Creating workflow: {request.workflow_id}")

    try:
        from app.services.agent_orchestration import WorkflowStep, AgentAction

        steps = []
        for i, step_req in enumerate(request.steps):
            action = AgentAction(
                id=f"action-{i}",
                agent_id=step_req.agent_id,
                action_type=step_req.action_type,
                description=step_req.description,
                parameters=step_req.parameters,
                safety_level=SafetyLevel(step_req.safety_level),
                requires_approval=step_req.requires_approval,
                approval_chain=step_req.approval_chain,
            )

            step = WorkflowStep(
                id=f"step-{i}",
                agent_id=step_req.agent_id,
                action=action,
            )

            steps.append(step)

        await orchestrator.create_workflow(request.workflow_id, steps)

        return {
            "workflow_id": request.workflow_id,
            "status": "created",
            "steps": len(steps),
        }

    except Exception as e:
        logger.error(f"Workflow creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow creation failed: {str(e)}",
        )


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Execute a workflow.

    Args:
        workflow_id: Workflow ID
        db: Database session

    Returns:
        Execution result
    """
    logger.info(f"Executing workflow: {workflow_id}")

    try:
        result = await orchestrator.execute_workflow(workflow_id)

        return result.to_dict()

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.get("/executions/{execution_id}")
async def get_execution_status(
    execution_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get execution status.

    Args:
        execution_id: Execution ID
        db: Database session

    Returns:
        Execution status
    """
    logger.info(f"Getting execution status: {execution_id}")

    try:
        result = await orchestrator.get_execution_status(execution_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Getting execution status failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting execution status failed: {str(e)}",
        )


@router.post("/approvals/request")
async def request_approval(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Request approval for an action.

    Args:
        request: Approval request
        db: Database session

    Returns:
        Approval request ID
    """
    logger.info(f"Requesting approval for action: {request.action_id}")

    try:
        approval_id = await orchestrator.request_approval(
            action_id=request.action_id,
            agent_id="system",  # TODO: Get from context
            description=request.description,
            required_approvers=request.required_approvers,
            safety_level=SafetyLevel(request.safety_level),
        )

        return {
            "approval_id": approval_id,
            "status": "requested",
            "action_id": request.action_id,
        }

    except Exception as e:
        logger.error(f"Approval request failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval request failed: {str(e)}",
        )


@router.get("/approvals/pending")
async def get_pending_approvals(
    approver: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get pending approvals.

    Args:
        approver: Filter by approver
        db: Database session

    Returns:
        Pending approval requests
    """
    logger.info(f"Getting pending approvals (approver={approver})")

    try:
        approvals = await orchestrator.get_pending_approvals(approver)

        return {
            "total": len(approvals),
            "pending": [
                {
                    "id": a.id,
                    "action_id": a.action_id,
                    "description": a.description,
                    "requested_at": a.requested_at.isoformat(),
                    "safety_level": a.approval_level.value,
                }
                for a in approvals
            ],
        }

    except Exception as e:
        logger.error(f"Getting pending approvals failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting pending approvals failed: {str(e)}",
        )


@router.post("/approvals/{approval_id}/respond")
async def respond_to_approval(
    approval_id: str,
    request: ApprovalResponseRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Respond to an approval request.

    Args:
        approval_id: Approval ID
        request: Response request
        db: Database session

    Returns:
        Response confirmation
    """
    logger.info(f"Responding to approval: {approval_id}")

    try:
        if request.action == "approve":
            result = await orchestrator.approve_action(approval_id, request.approved_by)
        elif request.action == "reject":
            result = await orchestrator.reject_action(
                approval_id, request.approved_by, request.reason or "No reason provided"
            )
        else:
            raise ValueError(f"Invalid action: {request.action}")

        return {
            "approval_id": approval_id,
            "action": request.action,
            "status": "processed" if result else "not_found",
        }

    except Exception as e:
        logger.error(f"Approval response failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval response failed: {str(e)}",
        )
