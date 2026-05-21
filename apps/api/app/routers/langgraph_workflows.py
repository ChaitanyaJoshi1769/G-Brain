"""
LangGraph Workflow Endpoints

Provides endpoints for creating and executing stateful, persistent agent workflows.
Enables complex reasoning chains and multi-agent collaboration.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.langgraph_agents import (
    LangGraphAgentBuilder,
    AgentPool,
    ReasoningMode,
    ThinkingStep,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global agent pool
agent_pool = AgentPool()


class AgentWorkflowRequest(BaseModel):
    """Agent workflow creation request."""
    agent_id: str
    reasoning_mode: str
    task: str
    context: dict = Field(default_factory=dict)
    nodes: List[dict] = Field(default_factory=list)


class WorkflowNodeRequest(BaseModel):
    """Workflow node definition."""
    node_id: str
    node_type: str  # "thinking", "tool", "decision"
    tool_name: Optional[str] = None
    description: str = ""


class WorkflowEdgeRequest(BaseModel):
    """Workflow edge definition."""
    from_node: str
    to_node: str
    condition: Optional[str] = None


class AgentExecutionRequest(BaseModel):
    """Agent execution request."""
    agent_id: str
    task: str
    context: dict = Field(default_factory=dict)


class MultiAgentRequest(BaseModel):
    """Multi-agent coordination request."""
    task: str
    agent_ids: List[str]
    strategy: str = "sequential"  # sequential or parallel


class WorkflowResponse(BaseModel):
    """Workflow execution response."""
    agent_id: str
    status: str
    task: str
    thinking_chain_length: int
    tool_calls: int
    execution_time_ms: float


@router.post("/agents")
async def create_workflow_agent(
    request: AgentWorkflowRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Create a new agent with workflow.

    Args:
        request: Agent workflow request
        db: Database session

    Returns:
        Agent creation confirmation
    """
    logger.info(f"Creating agent: {request.agent_id}")

    try:
        reasoning_mode = ReasoningMode(request.reasoning_mode)

        builder = await agent_pool.register_agent(request.agent_id, reasoning_mode)

        # Add nodes
        for node in request.nodes:
            node_type = node.get("node_type")
            node_id = node.get("node_id")

            if node_type == "thinking":
                builder.add_thinking_node(node_id)
            elif node_type == "decision":
                builder.add_decision_node(node_id)
            elif node_type == "tool":
                # TODO: Get actual tool function from registry
                async def mock_tool(**kwargs):
                    return {"status": "executed"}

                tool_name = node.get("tool_name", node_id)
                builder.add_tool_node(node_id, tool_name, mock_tool)

        return {
            "agent_id": request.agent_id,
            "reasoning_mode": request.reasoning_mode,
            "status": "created",
            "nodes": len(request.nodes),
        }

    except Exception as e:
        logger.error(f"Agent creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent creation failed: {str(e)}",
        )


@router.post("/agents/{agent_id}/execute")
async def execute_agent_workflow(
    agent_id: str,
    request: AgentExecutionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowResponse:
    """
    Execute an agent workflow.

    Args:
        agent_id: Agent ID
        request: Execution request
        db: Database session

    Returns:
        Execution result
    """
    logger.info(f"Executing agent: {agent_id}")

    try:
        if agent_id not in agent_pool.agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        import time

        start_time = time.time()
        agent = agent_pool.agents[agent_id]
        result = await agent.build_and_execute(request.task, request.context)
        duration_ms = (time.time() - start_time) * 1000

        return WorkflowResponse(
            agent_id=agent_id,
            status=result["status"],
            task=request.task,
            thinking_chain_length=len(result["thinking_chain"]),
            tool_calls=len(result["tool_calls"]),
            execution_time_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get agent metrics.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Agent metrics
    """
    logger.info(f"Getting metrics for agent: {agent_id}")

    try:
        metrics = await agent_pool.get_agent_metrics(agent_id)

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        return metrics

    except Exception as e:
        logger.error(f"Getting metrics failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting metrics failed: {str(e)}",
        )


@router.post("/multi-agent/coordinate")
async def coordinate_multi_agent(
    request: MultiAgentRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Coordinate multiple agents.

    Args:
        request: Multi-agent coordination request
        db: Database session

    Returns:
        Coordination result
    """
    logger.info(f"Coordinating agents: {request.agent_ids}")

    try:
        result = await agent_pool.coordinate_agents(
            request.task, request.agent_ids, request.strategy
        )

        return {
            "task": request.task,
            "strategy": request.strategy,
            "agents": request.agent_ids,
            "status": "completed",
            "agents_executed": list(result["results"].keys()),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Agent coordination failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent coordination failed: {str(e)}",
        )


@router.get("/collaboration-history")
async def get_collaboration_history(
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get agent collaboration history.

    Args:
        limit: Maximum number of records
        db: Database session

    Returns:
        Collaboration history
    """
    logger.info(f"Getting collaboration history (limit={limit})")

    try:
        history = agent_pool.get_collaboration_history()
        latest = history[-limit:] if limit else history

        return {
            "total": len(history),
            "returned": len(latest),
            "history": [
                {
                    "timestamp": h["timestamp"],
                    "task": h["task"],
                    "agents": h["agents"],
                    "strategy": h["strategy"],
                }
                for h in latest
            ],
        }

    except Exception as e:
        logger.error(f"Getting history failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting history failed: {str(e)}",
        )


@router.get("/agents")
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    List all agents in the pool.

    Args:
        db: Database session

    Returns:
        List of agents
    """
    logger.info("Listing agents")

    try:
        agents_info = []
        for agent_id, agent in agent_pool.agents.items():
            agents_info.append(
                {
                    "agent_id": agent_id,
                    "reasoning_mode": agent.reasoning_mode.value,
                    "nodes": len(agent.nodes),
                    "tools": len(agent.tools),
                }
            )

        return {
            "total": len(agents_info),
            "agents": agents_info,
        }

    except Exception as e:
        logger.error(f"Listing agents failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Listing agents failed: {str(e)}",
        )


@router.get("/agents/{agent_id}")
async def get_agent_details(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get agent details.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Agent details
    """
    logger.info(f"Getting agent details: {agent_id}")

    try:
        if agent_id not in agent_pool.agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        agent = agent_pool.agents[agent_id]

        return {
            "agent_id": agent_id,
            "reasoning_mode": agent.reasoning_mode.value,
            "nodes": list(agent.nodes.keys()),
            "edges": [
                {"from": f, "to": t} for f, t in agent.edges
            ],
            "tools": list(agent.tools.keys()),
            "memory": {
                "short_term": len(agent.memory.short_term),
                "long_term": len(agent.memory.long_term),
                "facts": len(agent.memory.facts),
            },
        }

    except Exception as e:
        logger.error(f"Getting agent details failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting agent details failed: {str(e)}",
        )
