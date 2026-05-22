"""
Audit & Compliance API Router

Provides endpoints for audit trails, compliance checking, and reporting.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from apps.api.app.services.audit_compliance import (
    audit_logger,
    compliance_checker,
    AuditEvent,
    EventType,
    ResourceType,
)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/trail")
async def get_audit_trail(
    event_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """
    Get audit trail with optional filtering.

    Args:
        event_type: Filter by event type (create, update, delete, execute, access)
        resource_type: Filter by resource type (agent, skill, workflow, etc.)
        resource_id: Filter by resource ID
        actor_id: Filter by actor ID
        tenant_id: Filter by tenant ID
        limit: Maximum number of records

    Returns:
        Filtered audit trail events
    """
    filters = {}
    if event_type:
        filters["event_type"] = event_type
    if resource_type:
        filters["resource_type"] = resource_type
    if resource_id:
        filters["resource_id"] = resource_id
    if actor_id:
        filters["actor_id"] = actor_id
    if tenant_id:
        filters["tenant_id"] = tenant_id

    events = audit_logger.get_events(filters=filters, limit=limit)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "filters_applied": filters,
        "total_events": len(events),
        "events": events,
    }


@router.get("/trail/resource/{resource_id}")
async def get_resource_audit_trail(
    resource_id: str,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get audit trail for a specific resource.

    Args:
        resource_id: The resource ID
        limit: Maximum number of records

    Returns:
        All audit events related to the resource
    """
    events = audit_logger.get_events(
        filters={"resource_id": resource_id},
        limit=limit
    )

    return {
        "resource_id": resource_id,
        "timestamp": datetime.utcnow().isoformat(),
        "total_events": len(events),
        "events": events,
    }


@router.get("/trail/actor/{actor_id}")
async def get_actor_audit_trail(
    actor_id: str,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get audit trail for actions by a specific actor.

    Args:
        actor_id: The actor ID (user or service)
        limit: Maximum number of records

    Returns:
        All audit events by the actor
    """
    events = audit_logger.get_events(
        filters={"actor_id": actor_id},
        limit=limit
    )

    return {
        "actor_id": actor_id,
        "timestamp": datetime.utcnow().isoformat(),
        "total_events": len(events),
        "events": events,
    }


@router.post("/log-event")
async def log_audit_event(
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor_id: str,
    status: str = "success",
    error_message: Optional[str] = None,
    tenant_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Manually log an audit event.

    Args:
        event_type: Type of event (create, update, delete, execute, access)
        resource_type: Type of resource being audited
        resource_id: ID of the resource
        actor_id: ID of the actor performing the action
        status: Success or failure status
        error_message: Optional error message
        tenant_id: Optional tenant ID
        metadata: Optional additional metadata

    Returns:
        Confirmation of logged event
    """
    try:
        evt = AuditEvent(
            event_id=f"evt-{id(object())}",
            event_type=EventType(event_type),
            resource_type=ResourceType(resource_type),
            resource_id=resource_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            status=status,
            error_message=error_message,
            metadata=metadata or {},
        )
        audit_logger.log_event(evt)

        return {
            "event_id": evt.event_id,
            "logged": True,
            "logged_at": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid event type or resource type: {str(e)}")


@router.get("/export")
async def export_audit_trail(
    tenant_id: Optional[str] = None,
    format: str = Query("json", regex="^(json)$")
) -> Dict[str, Any]:
    """
    Export complete audit trail.

    Args:
        tenant_id: Optional tenant ID to filter export
        format: Export format (json for now)

    Returns:
        Complete audit trail in requested format
    """
    return audit_logger.export_audit_trail(tenant_id=tenant_id)


@router.get("/compliance/report")
async def get_compliance_report(
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate compliance report.

    Args:
        tenant_id: Optional tenant ID for tenant-specific report

    Returns:
        Comprehensive compliance report with all checks
    """
    return compliance_checker.generate_compliance_report(tenant_id=tenant_id)


@router.get("/compliance/retention")
async def check_data_retention() -> Dict[str, Any]:
    """
    Check data retention compliance.

    Returns:
        Data retention policy compliance status and violations
    """
    return compliance_checker.check_data_retention_compliance()


@router.get("/compliance/isolation")
async def check_isolation() -> Dict[str, Any]:
    """
    Check multi-tenancy isolation compliance.

    Returns:
        Multi-tenancy isolation status
    """
    return compliance_checker.validate_multi_tenancy_isolation()


@router.get("/compliance/access-control")
async def check_access_control() -> Dict[str, Any]:
    """
    Check access control compliance.

    Returns:
        Access control verification results
    """
    return compliance_checker.verify_access_control()


@router.get("/statistics")
async def get_audit_statistics(
    time_window_days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get audit statistics for a time window.

    Args:
        time_window_days: Time window in days

    Returns:
        Statistics about audit events in the window
    """
    cutoff_time = datetime.utcnow() - timedelta(days=time_window_days)
    recent_events = [e for e in audit_logger.events if e.timestamp >= cutoff_time]

    # Calculate statistics
    event_type_counts = {}
    resource_type_counts = {}
    actor_counts = {}
    status_counts = {"success": 0, "failure": 0}

    for event in recent_events:
        # Count by event type
        event_type_counts[event.event_type.value] = event_type_counts.get(
            event.event_type.value, 0
        ) + 1

        # Count by resource type
        resource_type_counts[event.resource_type.value] = resource_type_counts.get(
            event.resource_type.value, 0
        ) + 1

        # Count by actor
        actor_counts[event.actor_id] = actor_counts.get(event.actor_id, 0) + 1

        # Count by status
        if event.status == "success":
            status_counts["success"] += 1
        else:
            status_counts["failure"] += 1

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "time_window_days": time_window_days,
        "total_events": len(recent_events),
        "by_event_type": event_type_counts,
        "by_resource_type": resource_type_counts,
        "by_status": status_counts,
        "unique_actors": len(actor_counts),
        "top_actors": sorted(
            [(k, v) for k, v in actor_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10],
    }


@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(50, ge=1, le=500)
) -> Dict[str, Any]:
    """
    Get most recent audit events.

    Args:
        limit: Maximum number of recent events

    Returns:
        Most recent audit events
    """
    recent = audit_logger.events[-limit:] if limit else audit_logger.events

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "returned_count": len(recent),
        "total_events": len(audit_logger.events),
        "events": [e.to_dict() for e in recent],
    }


@router.get("/health")
async def audit_system_health() -> Dict[str, Any]:
    """
    Get audit system health status.

    Returns:
        Health status of the audit system
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "operational",
        "total_events_logged": len(audit_logger.events),
        "compliance_status": compliance_checker.generate_compliance_report(),
        "masking_enabled": audit_logger.masker is not None,
    }
