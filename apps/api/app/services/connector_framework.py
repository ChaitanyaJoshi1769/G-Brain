"""
Connector Framework Service

Provides base classes and interfaces for building custom integrations.
Enables extensibility without modifying core code.
"""

import logging
import asyncio
from typing import Optional, Dict, List, Any, Callable, Awaitable, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)


class ConnectorType(str, Enum):
    """Types of connectors."""
    WEBHOOK = "webhook"
    API = "api"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    EMAIL = "email"
    SLACK = "slack"
    CUSTOM = "custom"


class AuthType(str, Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH = "oauth"


@dataclass
class ConnectorConfig:
    """Configuration for a connector instance."""
    name: str
    connector_type: ConnectorType
    base_url: Optional[str] = None
    auth_type: AuthType = AuthType.NONE
    credentials: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    enabled: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, mask_credentials: bool = True) -> Dict[str, Any]:
        """Convert to dictionary."""
        creds = self.credentials.copy()
        if mask_credentials:
            creds = {k: "[REDACTED]" for k in creds.keys()}

        return {
            "name": self.name,
            "connector_type": self.connector_type.value,
            "base_url": self.base_url,
            "auth_type": self.auth_type.value,
            "credentials": creds,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "enabled": self.enabled,
        }


class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.is_connected = False
        self.last_error: Optional[str] = None
        self.connection_time: Optional[datetime] = None

    @abstractmethod
    async def validate(self) -> bool:
        """Validate connector configuration and connectivity."""
        pass

    @abstractmethod
    async def send(self, data: Dict[str, Any]) -> bool:
        """Send data through connector."""
        pass

    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive data from connector."""
        pass

    async def transform(self, data: Dict[str, Any], direction: str = "send") -> Dict[str, Any]:
        """Transform data format (can be overridden by subclasses)."""
        return data

    async def connect(self) -> bool:
        """Establish connection."""
        try:
            if await self.validate():
                self.is_connected = True
                self.connection_time = datetime.utcnow()
                logger.info(f"Connector {self.config.name} connected successfully")
                return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect {self.config.name}: {e}")
        return False

    async def disconnect(self) -> None:
        """Disconnect from service."""
        self.is_connected = False
        logger.info(f"Connector {self.config.name} disconnected")

    def get_status(self) -> Dict[str, Any]:
        """Get connector status."""
        return {
            "name": self.config.name,
            "type": self.config.connector_type.value,
            "connected": self.is_connected,
            "enabled": self.config.enabled,
            "last_error": self.last_error,
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
        }


@dataclass
class ConnectorLog:
    """Log entry for connector execution."""
    connector_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    operation: str = "send"
    success: bool = True
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    data_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connector_id": self.connector_id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "data_size_bytes": self.data_size_bytes,
        }


class ConnectorRegistry:
    """Registry for available connector types."""

    def __init__(self):
        self.connectors: Dict[str, Type[BaseConnector]] = {}
        self.instances: Dict[str, BaseConnector] = {}
        self._register_builtin_connectors()

    def register(self, name: str, connector_class: Type[BaseConnector]) -> None:
        """Register a connector type."""
        self.connectors[name] = connector_class
        logger.info(f"Connector registered: {name}")

    def get_connector_class(self, name: str) -> Optional[Type[BaseConnector]]:
        """Get connector class by name."""
        return self.connectors.get(name)

    def list_connectors(self) -> List[str]:
        """List available connector types."""
        return list(self.connectors.keys())

    def _register_builtin_connectors(self) -> None:
        """Register built-in connectors."""
        # These would be actual implementations in a real system
        logger.info("Built-in connectors registered")


class ConnectorManager:
    """Manage connector instances."""

    def __init__(self, registry: ConnectorRegistry):
        self.registry = registry
        self.connectors: Dict[str, BaseConnector] = {}
        self.logs: List[ConnectorLog] = []
        self.tenant_connectors: Dict[str, List[str]] = {}  # tenant_id -> connector_ids

    async def create_connector(
        self, connector_id: str, config: ConnectorConfig, tenant_id: Optional[str] = None
    ) -> Optional[BaseConnector]:
        """Create and register a connector instance."""
        try:
            connector_class = self.registry.get_connector_class(config.connector_type.value)
            if not connector_class:
                logger.error(f"Unknown connector type: {config.connector_type.value}")
                return None

            connector = connector_class(config)
            if await connector.connect():
                self.connectors[connector_id] = connector

                # Track tenant ownership
                if tenant_id:
                    if tenant_id not in self.tenant_connectors:
                        self.tenant_connectors[tenant_id] = []
                    self.tenant_connectors[tenant_id].append(connector_id)

                logger.info(f"Connector created: {connector_id}")
                return connector
        except Exception as e:
            logger.error(f"Failed to create connector {connector_id}: {e}")

        return None

    async def delete_connector(self, connector_id: str) -> bool:
        """Delete a connector instance."""
        if connector_id in self.connectors:
            connector = self.connectors[connector_id]
            await connector.disconnect()
            del self.connectors[connector_id]
            logger.info(f"Connector deleted: {connector_id}")
            return True
        return False

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        """Get connector instance."""
        return self.connectors.get(connector_id)

    def list_connectors(self, tenant_id: Optional[str] = None) -> List[str]:
        """List connector IDs."""
        if tenant_id:
            return self.tenant_connectors.get(tenant_id, [])
        return list(self.connectors.keys())

    async def send_data(
        self, connector_id: str, data: Dict[str, Any]
    ) -> bool:
        """Send data through a connector."""
        connector = self.get_connector(connector_id)
        if not connector:
            logger.warning(f"Connector not found: {connector_id}")
            return False

        log_entry = ConnectorLog(
            connector_id=connector_id,
            operation="send",
            data_size_bytes=len(json.dumps(data)),
        )

        try:
            import time
            start_time = time.time()

            if not connector.is_connected:
                if not await connector.connect():
                    raise Exception("Failed to connect")

            # Transform data
            transformed_data = await connector.transform(data, direction="send")

            # Send with retries
            success = False
            last_error = None
            for attempt in range(connector.config.retry_attempts):
                try:
                    success = await connector.send(transformed_data)
                    if success:
                        break
                except Exception as e:
                    last_error = str(e)
                    if attempt < connector.config.retry_attempts - 1:
                        await asyncio.sleep(connector.config.retry_backoff_seconds)

            if not success and last_error:
                raise Exception(last_error)

            log_entry.success = True
            log_entry.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            log_entry.success = False
            log_entry.error_message = str(e)
            logger.error(f"Failed to send data via {connector_id}: {e}")

        self.logs.append(log_entry)
        return log_entry.success

    async def test_connector(self, connector_id: str) -> Dict[str, Any]:
        """Test connector connectivity."""
        connector = self.get_connector(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        try:
            is_valid = await connector.validate()
            return {
                "success": is_valid,
                "status": connector.get_status(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_connector_logs(
        self, connector_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get connector execution logs."""
        logs = self.logs
        if connector_id:
            logs = [l for l in logs if l.connector_id == connector_id]

        return [l.to_dict() for l in logs[-limit:]]

    def get_connector_status(self, connector_id: str) -> Optional[Dict[str, Any]]:
        """Get connector status."""
        connector = self.get_connector(connector_id)
        if connector:
            return connector.get_status()
        return None


# Concrete connector implementations

class WebhookConnector(BaseConnector):
    """Connector for HTTP webhooks."""

    async def validate(self) -> bool:
        """Validate webhook endpoint."""
        if not self.config.base_url:
            self.last_error = "No base_url configured"
            return False
        return True

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send data via webhook."""
        # In real implementation, would make HTTP request
        logger.info(f"Webhook connector {self.config.name} would send: {data}")
        return True

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive webhook data."""
        return None


class EmailConnector(BaseConnector):
    """Connector for email notifications."""

    async def validate(self) -> bool:
        """Validate email configuration."""
        required_fields = ["smtp_host", "smtp_port", "from_email"]
        if not all(field in self.config.credentials for field in required_fields):
            self.last_error = f"Missing required fields: {required_fields}"
            return False
        return True

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send email."""
        # In real implementation, would send actual email
        logger.info(f"Email connector {self.config.name} would send email with: {data}")
        return True

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive emails."""
        return None


class SlackConnector(BaseConnector):
    """Connector for Slack integration."""

    async def validate(self) -> bool:
        """Validate Slack configuration."""
        if "webhook_url" not in self.config.credentials:
            self.last_error = "Missing webhook_url in credentials"
            return False
        return True

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send Slack message."""
        # In real implementation, would call Slack API
        message = data.get("text", "")
        logger.info(f"Slack connector {self.config.name} would send: {message}")
        return True

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive Slack events."""
        return None


class DatabaseConnector(BaseConnector):
    """Connector for database operations."""

    async def validate(self) -> bool:
        """Validate database configuration."""
        required_fields = ["connection_string"]
        if not all(field in self.config.credentials for field in required_fields):
            self.last_error = f"Missing required fields: {required_fields}"
            return False
        return True

    async def send(self, data: Dict[str, Any]) -> bool:
        """Write data to database."""
        # In real implementation, would execute database operation
        logger.info(f"Database connector {self.config.name} would write: {data}")
        return True

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Read data from database."""
        return None


# Global connector manager
connector_registry = ConnectorRegistry()

# Register built-in connectors
connector_registry.register("webhook", WebhookConnector)
connector_registry.register("email", EmailConnector)
connector_registry.register("slack", SlackConnector)
connector_registry.register("database", DatabaseConnector)

connector_manager = ConnectorManager(connector_registry)
