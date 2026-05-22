"""
Connectors API Router

Provides endpoints for managing custom integrations and connectors.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from apps.api.app.services.connector_framework import (
    connector_manager,
    connector_registry,
    ConnectorConfig,
    ConnectorType,
    AuthType,
)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


# Request/Response Models
class ConnectorConfigRequest(BaseModel):
    """Request model for connector creation/update."""
    name: str
    connector_type: str
    base_url: Optional[str] = None
    auth_type: str = "none"
    credentials: Dict[str, str] = {}
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    enabled: bool = True
    custom_settings: Dict[str, Any] = {}


class ConnectorResponse(BaseModel):
    """Response model for connector details."""
    id: str
    name: str
    connector_type: str
    enabled: bool
    status: str
    connected: bool
    last_error: Optional[str] = None


# API Endpoints

@router.get("")
async def list_connectors(
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all available connectors.

    Args:
        tenant_id: Optional tenant ID to filter connectors

    Returns:
        List of connector IDs and basic information
    """
    connector_ids = connector_manager.list_connectors(tenant_id=tenant_id)
    connectors = []

    for conn_id in connector_ids:
        status = connector_manager.get_connector_status(conn_id)
        if status:
            connectors.append({
                "id": conn_id,
                **status,
            })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id,
        "total_connectors": len(connectors),
        "connectors": connectors,
    }


@router.post("")
async def create_connector(
    request: ConnectorConfigRequest,
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new connector instance.

    Args:
        request: Connector configuration
        tenant_id: Optional tenant ID for ownership

    Returns:
        Created connector details
    """
    try:
        # Convert to ConnectorConfig
        connector_type = ConnectorType(request.connector_type)
        auth_type = AuthType(request.auth_type)

        config = ConnectorConfig(
            name=request.name,
            connector_type=connector_type,
            base_url=request.base_url,
            auth_type=auth_type,
            credentials=request.credentials,
            timeout_seconds=request.timeout_seconds,
            retry_attempts=request.retry_attempts,
            retry_backoff_seconds=request.retry_backoff_seconds,
            enabled=request.enabled,
            custom_settings=request.custom_settings,
        )

        # Create unique ID
        connector_id = f"conn-{id(object())}"

        # Create connector
        connector = await connector_manager.create_connector(
            connector_id, config, tenant_id=tenant_id
        )

        if connector is None:
            raise HTTPException(status_code=400, detail="Failed to create connector")

        return {
            "id": connector_id,
            "name": config.name,
            "connector_type": connector_type.value,
            "enabled": config.enabled,
            "created_at": datetime.utcnow().isoformat(),
            "status": connector.get_status(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create connector: {str(e)}")


@router.get("/{connector_id}")
async def get_connector(connector_id: str) -> Dict[str, Any]:
    """
    Get connector details.

    Args:
        connector_id: The connector ID

    Returns:
        Connector configuration and status
    """
    connector = connector_manager.get_connector(connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

    status = connector.get_status()
    return {
        "id": connector_id,
        "config": connector.config.to_dict(mask_credentials=True),
        **status,
    }


@router.put("/{connector_id}")
async def update_connector(
    connector_id: str,
    request: ConnectorConfigRequest
) -> Dict[str, Any]:
    """
    Update connector configuration.

    Args:
        connector_id: The connector ID
        request: Updated configuration

    Returns:
        Updated connector details
    """
    connector = connector_manager.get_connector(connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

    # Update configuration
    connector.config.name = request.name
    connector.config.timeout_seconds = request.timeout_seconds
    connector.config.retry_attempts = request.retry_attempts
    connector.config.retry_backoff_seconds = request.retry_backoff_seconds
    connector.config.enabled = request.enabled

    if request.credentials:
        connector.config.credentials.update(request.credentials)

    return {
        "id": connector_id,
        "updated_at": datetime.utcnow().isoformat(),
        "config": connector.config.to_dict(mask_credentials=True),
        "status": connector.get_status(),
    }


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str) -> Dict[str, Any]:
    """
    Delete a connector.

    Args:
        connector_id: The connector ID to delete

    Returns:
        Deletion confirmation
    """
    result = await connector_manager.delete_connector(connector_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

    return {
        "id": connector_id,
        "deleted": True,
        "deleted_at": datetime.utcnow().isoformat(),
    }


@router.post("/{connector_id}/test")
async def test_connector(connector_id: str) -> Dict[str, Any]:
    """
    Test connector connectivity.

    Args:
        connector_id: The connector ID to test

    Returns:
        Test result with status and error information
    """
    result = await connector_manager.test_connector(connector_id)
    return {
        "id": connector_id,
        **result,
    }


@router.post("/{connector_id}/send")
async def send_via_connector(
    connector_id: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send data through a connector.

    Args:
        connector_id: The connector ID
        data: Data to send

    Returns:
        Send operation result
    """
    result = await connector_manager.send_data(connector_id, data)

    return {
        "id": connector_id,
        "success": result,
        "sent_at": datetime.utcnow().isoformat(),
    }


@router.get("/{connector_id}/logs")
async def get_connector_logs(
    connector_id: str,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get execution logs for a connector.

    Args:
        connector_id: The connector ID
        limit: Maximum number of logs to return

    Returns:
        Connector execution logs
    """
    logs = connector_manager.get_connector_logs(connector_id=connector_id, limit=limit)

    return {
        "id": connector_id,
        "total_logs": len(logs),
        "logs": logs,
    }


@router.get("/types/available")
async def list_available_connector_types() -> Dict[str, Any]:
    """
    List available connector types that can be created.

    Returns:
        Available connector types and their descriptions
    """
    available_types = {
        "webhook": "HTTP webhook for sending/receiving data",
        "email": "Email integration for notifications",
        "slack": "Slack integration for messaging",
        "database": "Database connector for read/write operations",
        "api": "Generic REST API connector",
        "message_queue": "Message queue integration",
        "custom": "Custom connector implementation",
    }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "types": available_types,
        "count": len(available_types),
    }


@router.get("/types/{connector_type}/schema")
async def get_connector_schema(connector_type: str) -> Dict[str, Any]:
    """
    Get configuration schema for a connector type.

    Args:
        connector_type: The connector type

    Returns:
        Configuration schema and required/optional fields
    """
    schemas = {
        "webhook": {
            "required": ["base_url"],
            "optional": ["auth_type", "timeout_seconds"],
            "example": {
                "name": "My Webhook",
                "base_url": "https://example.com/webhook",
                "auth_type": "bearer",
            },
        },
        "email": {
            "required": ["smtp_host", "smtp_port", "from_email"],
            "optional": ["auth_type"],
            "example": {
                "name": "Email Notifier",
                "credentials": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": "587",
                    "from_email": "bot@example.com",
                },
            },
        },
        "slack": {
            "required": ["webhook_url"],
            "optional": ["channel"],
            "example": {
                "name": "Slack Integration",
                "credentials": {
                    "webhook_url": "https://hooks.slack.com/services/...",
                },
            },
        },
        "database": {
            "required": ["connection_string"],
            "optional": ["timeout_seconds"],
            "example": {
                "name": "PostgreSQL",
                "credentials": {
                    "connection_string": "postgresql://user:pass@localhost/db",
                },
            },
        },
    }

    if connector_type not in schemas:
        raise HTTPException(
            status_code=404,
            detail=f"No schema found for connector type: {connector_type}"
        )

    return {
        "connector_type": connector_type,
        "schema": schemas[connector_type],
    }


@router.post("/bulk/send")
async def bulk_send(
    connectors: List[str],
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send data through multiple connectors.

    Args:
        connectors: List of connector IDs
        data: Data to send

    Returns:
        Results for each connector
    """
    results = {}
    for connector_id in connectors:
        success = await connector_manager.send_data(connector_id, data)
        results[connector_id] = {"success": success}

    successful = sum(1 for r in results.values() if r["success"])
    failed = len(results) - successful

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    }
