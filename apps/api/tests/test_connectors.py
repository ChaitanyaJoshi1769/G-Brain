"""
Tests for Connector Framework
"""

import pytest
import asyncio
from apps.api.app.services.connector_framework import (
    ConnectorType,
    AuthType,
    ConnectorConfig,
    BaseConnector,
    ConnectorRegistry,
    ConnectorManager,
    WebhookConnector,
    EmailConnector,
    SlackConnector,
    DatabaseConnector,
)


class TestConnectorConfig:
    """Test connector configuration."""

    def test_config_creation(self):
        """Test creating connector config."""
        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        assert config.name == "test-webhook"
        assert config.enabled is True

    def test_config_with_credentials(self):
        """Test config with credentials."""
        config = ConnectorConfig(
            name="test-email",
            connector_type=ConnectorType.EMAIL,
            auth_type=AuthType.BASIC,
            credentials={"smtp_host": "smtp.example.com", "password": "secret"},
        )
        assert "smtp_host" in config.credentials

    def test_config_to_dict_masks_credentials(self):
        """Test that to_dict masks credentials."""
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.API,
            credentials={"api_key": "secret123"},
        )
        result = config.to_dict(mask_credentials=True)
        assert result["credentials"]["api_key"] == "[REDACTED]"

    def test_config_to_dict_shows_credentials(self):
        """Test that to_dict can show credentials."""
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.API,
            credentials={"api_key": "secret123"},
        )
        result = config.to_dict(mask_credentials=False)
        assert result["credentials"]["api_key"] == "secret123"


class TestConnectorRegistry:
    """Test connector registry."""

    def test_registry_creation(self):
        """Test creating registry."""
        registry = ConnectorRegistry()
        assert len(registry.list_connectors()) >= 4  # Built-in connectors

    def test_register_connector(self):
        """Test registering a connector."""
        registry = ConnectorRegistry()
        initial_count = len(registry.list_connectors())

        class CustomConnector(BaseConnector):
            async def validate(self):
                return True

            async def send(self, data):
                return True

            async def receive(self):
                return None

        registry.register("custom", CustomConnector)
        assert len(registry.list_connectors()) == initial_count + 1

    def test_get_connector_class(self):
        """Test getting connector class."""
        registry = ConnectorRegistry()
        webhook_class = registry.get_connector_class("webhook")
        assert webhook_class is not None
        assert webhook_class == WebhookConnector

    def test_list_connectors(self):
        """Test listing available connectors."""
        registry = ConnectorRegistry()
        connectors = registry.list_connectors()
        assert "webhook" in connectors
        assert "email" in connectors
        assert "slack" in connectors
        assert "database" in connectors


@pytest.mark.asyncio
class TestWebhookConnector:
    """Test webhook connector."""

    async def test_webhook_validation(self):
        """Test webhook connector validation."""
        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        connector = WebhookConnector(config)
        assert await connector.validate() is True

    async def test_webhook_missing_url(self):
        """Test webhook validation without URL."""
        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
        )
        connector = WebhookConnector(config)
        assert await connector.validate() is False

    async def test_webhook_send(self):
        """Test webhook send."""
        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        connector = WebhookConnector(config)
        result = await connector.send({"message": "test"})
        assert result is True


@pytest.mark.asyncio
class TestEmailConnector:
    """Test email connector."""

    async def test_email_validation_success(self):
        """Test email connector validation with credentials."""
        config = ConnectorConfig(
            name="test-email",
            connector_type=ConnectorType.EMAIL,
            credentials={
                "smtp_host": "smtp.example.com",
                "smtp_port": "587",
                "from_email": "noreply@example.com",
            },
        )
        connector = EmailConnector(config)
        assert await connector.validate() is True

    async def test_email_validation_missing_fields(self):
        """Test email validation without required fields."""
        config = ConnectorConfig(
            name="test-email",
            connector_type=ConnectorType.EMAIL,
        )
        connector = EmailConnector(config)
        assert await connector.validate() is False

    async def test_email_send(self):
        """Test email send."""
        config = ConnectorConfig(
            name="test-email",
            connector_type=ConnectorType.EMAIL,
            credentials={
                "smtp_host": "smtp.example.com",
                "smtp_port": "587",
                "from_email": "noreply@example.com",
            },
        )
        connector = EmailConnector(config)
        result = await connector.send({
            "to": "user@example.com",
            "subject": "Test",
            "body": "Test email",
        })
        assert result is True


@pytest.mark.asyncio
class TestSlackConnector:
    """Test Slack connector."""

    async def test_slack_validation_success(self):
        """Test Slack validation with webhook."""
        config = ConnectorConfig(
            name="test-slack",
            connector_type=ConnectorType.SLACK,
            credentials={"webhook_url": "https://hooks.slack.com/..."},
        )
        connector = SlackConnector(config)
        assert await connector.validate() is True

    async def test_slack_validation_missing_webhook(self):
        """Test Slack validation without webhook."""
        config = ConnectorConfig(
            name="test-slack",
            connector_type=ConnectorType.SLACK,
        )
        connector = SlackConnector(config)
        assert await connector.validate() is False

    async def test_slack_send(self):
        """Test Slack send."""
        config = ConnectorConfig(
            name="test-slack",
            connector_type=ConnectorType.SLACK,
            credentials={"webhook_url": "https://hooks.slack.com/..."},
        )
        connector = SlackConnector(config)
        result = await connector.send({"text": "Hello Slack"})
        assert result is True


@pytest.mark.asyncio
class TestDatabaseConnector:
    """Test database connector."""

    async def test_database_validation_success(self):
        """Test database validation with connection string."""
        config = ConnectorConfig(
            name="test-db",
            connector_type=ConnectorType.DATABASE,
            credentials={"connection_string": "postgresql://localhost/db"},
        )
        connector = DatabaseConnector(config)
        assert await connector.validate() is True

    async def test_database_validation_missing_connection(self):
        """Test database validation without connection string."""
        config = ConnectorConfig(
            name="test-db",
            connector_type=ConnectorType.DATABASE,
        )
        connector = DatabaseConnector(config)
        assert await connector.validate() is False

    async def test_database_send(self):
        """Test database write."""
        config = ConnectorConfig(
            name="test-db",
            connector_type=ConnectorType.DATABASE,
            credentials={"connection_string": "postgresql://localhost/db"},
        )
        connector = DatabaseConnector(config)
        result = await connector.send({"table": "agents", "data": {"id": "1"}})
        assert result is True


@pytest.mark.asyncio
class TestConnectorManager:
    """Test connector manager."""

    def test_connector_manager_creation(self):
        """Test creating connector manager."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)
        assert len(manager.connectors) == 0

    async def test_create_connector(self):
        """Test creating connector instance."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        connector = await manager.create_connector("conn-1", config)
        assert connector is not None
        assert manager.get_connector("conn-1") is not None

    async def test_create_connector_with_tenant(self):
        """Test creating connector with tenant ownership."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        await manager.create_connector("conn-1", config, tenant_id="tenant-1")

        tenant_connectors = manager.list_connectors(tenant_id="tenant-1")
        assert "conn-1" in tenant_connectors

    async def test_delete_connector(self):
        """Test deleting connector."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        await manager.create_connector("conn-1", config)
        assert manager.get_connector("conn-1") is not None

        result = await manager.delete_connector("conn-1")
        assert result is True
        assert manager.get_connector("conn-1") is None

    async def test_send_data(self):
        """Test sending data through connector."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        await manager.create_connector("conn-1", config)

        result = await manager.send_data("conn-1", {"message": "test"})
        assert result is True

    async def test_send_data_nonexistent_connector(self):
        """Test sending to nonexistent connector."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        result = await manager.send_data("nonexistent", {"message": "test"})
        assert result is False

    async def test_test_connector(self):
        """Test connector testing."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test-webhook",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        await manager.create_connector("conn-1", config)

        result = await manager.test_connector("conn-1")
        assert result["success"] is True

    def test_get_connector_logs(self):
        """Test getting connector logs."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        logs = manager.get_connector_logs()
        assert isinstance(logs, list)

    def test_get_connector_status(self):
        """Test getting connector status."""
        registry = ConnectorRegistry()
        manager = ConnectorManager(registry)

        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.WEBHOOK,
            base_url="https://example.com/webhook",
        )
        # Create synchronously
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.create_connector("conn-1", config))
        loop.close()

        status = manager.get_connector_status("conn-1")
        assert status is not None
        assert status["name"] == "test"
        assert "connected" in status
