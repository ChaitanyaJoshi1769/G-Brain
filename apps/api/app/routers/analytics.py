"""
Analytics API Router

Provides endpoints for metrics, performance analysis, and system health monitoring.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from apps.api.app.services.analytics_service import system_analytics

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/agents/{agent_id}/performance")
async def get_agent_performance(agent_id: str) -> Dict[str, Any]:
    """
    Get performance metrics for a specific agent.

    Args:
        agent_id: The agent ID to retrieve metrics for

    Returns:
        Performance metrics including execution count, success rate, durations
    """
    metrics = system_analytics.get_agent_performance(agent_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return metrics


@router.get("/agents")
async def get_all_agents_performance() -> List[Dict[str, Any]]:
    """
    Get performance metrics for all agents.

    Returns:
        List of agent performance metrics
    """
    return system_analytics.get_all_agents_performance()


@router.get("/system/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Get overall system health and KPIs.

    Returns:
        System health metrics including uptime, agent success rate, skill metrics
    """
    return system_analytics.get_system_health()


@router.get("/anomalies")
async def detect_anomalies(
    threshold_std_dev: float = Query(2.0, ge=0.5, le=5.0)
) -> Dict[str, Any]:
    """
    Detect performance anomalies in the system.

    Args:
        threshold_std_dev: Standard deviation threshold for anomaly detection

    Returns:
        List of detected anomalies with details
    """
    anomalies = system_analytics.detect_anomalies(threshold_std_dev)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "threshold_std_dev": threshold_std_dev,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


@router.get("/trends")
async def get_trends(
    time_window_hours: int = Query(24, ge=1, le=720)
) -> Dict[str, Any]:
    """
    Get performance trends over a time window.

    Args:
        time_window_hours: Time window in hours to analyze

    Returns:
        Trend analysis including active agents and performance metrics
    """
    return system_analytics.get_trends(time_window_hours)


@router.get("/workflows/{workflow_id}/metrics")
async def get_workflow_metrics(workflow_id: str) -> Dict[str, Any]:
    """
    Get metrics for a specific workflow.

    Args:
        workflow_id: The workflow ID to retrieve metrics for

    Returns:
        Workflow execution metrics and performance data
    """
    # Find workflow metrics from system analytics
    workflow_stats = system_analytics.workflow_metrics.to_dict()
    workflow_stats["workflow_id"] = workflow_id
    workflow_stats["retrieved_at"] = datetime.utcnow().isoformat()
    return workflow_stats


@router.post("/reports/export")
async def export_metrics_report(
    format: str = Query("json", regex="^(json|csv)$")
) -> Dict[str, Any]:
    """
    Export all metrics in specified format.

    Args:
        format: Export format (json or csv)

    Returns:
        Exported metrics in requested format
    """
    try:
        metrics = system_analytics.export_metrics(format=format)
        return {
            "export_time": datetime.utcnow().isoformat(),
            "format": format,
            "data": metrics,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/skills/metrics")
async def get_skill_metrics() -> Dict[str, Any]:
    """
    Get skill extraction metrics.

    Returns:
        Skill extraction performance and accuracy metrics
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        **system_analytics.skill_metrics.to_dict(),
    }


@router.get("/dashboard/summary")
async def get_dashboard_summary() -> Dict[str, Any]:
    """
    Get summary data for analytics dashboard.

    Returns:
        High-level overview of system metrics for dashboard display
    """
    health = system_analytics.get_system_health()
    anomalies = system_analytics.detect_anomalies()
    skills = system_analytics.skill_metrics.to_dict()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health": health,
        "anomalies": {
            "count": len(anomalies),
            "recent": anomalies[:5],  # Last 5 anomalies
        },
        "skills": {
            "total_extracted": skills["total_skills_extracted"],
            "success_rate": skills["extraction_success_rate"],
            "avg_confidence": skills["average_confidence_score"],
        },
        "agents": {
            "count": health["agent_count"],
            "success_rate": health["agent_success_rate"],
            "avg_duration_ms": health["average_agent_duration_ms"],
        },
    }


@router.get("/agent-comparison")
async def compare_agent_performance() -> Dict[str, Any]:
    """
    Compare performance metrics across agents.

    Returns:
        Ranked agents by various performance metrics
    """
    all_metrics = system_analytics.get_all_agents_performance()

    # Sort by success rate
    by_success = sorted(all_metrics, key=lambda x: x["success_rate"], reverse=True)
    # Sort by average duration (lower is better)
    by_speed = sorted(all_metrics, key=lambda x: x["average_duration_ms"])

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_agents": len(all_metrics),
        "by_success_rate": by_success,
        "by_speed": by_speed,
    }


@router.get("/performance-history")
async def get_performance_history(
    agent_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get historical performance data.

    Args:
        agent_id: Optional agent ID to get history for specific agent
        limit: Maximum number of records to return

    Returns:
        Historical performance data
    """
    if agent_id:
        if agent_id not in system_analytics.agent_analytics:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        analytics = system_analytics.agent_analytics[agent_id]
        history = analytics.get_recent_executions(limit=limit)
        return {
            "agent_id": agent_id,
            "record_count": len(history),
            "history": history,
        }
    else:
        # Return summary of all agents
        all_history = {}
        for agent_id, analytics in system_analytics.agent_analytics.items():
            all_history[agent_id] = len(analytics.execution_history)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_record_counts": all_history,
            "total_records": sum(all_history.values()),
        }
