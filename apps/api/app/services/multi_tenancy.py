"""
Multi-Tenancy Service

Enables G-Brain to support multiple organizations with complete isolation.
Implements tenant context, isolation, and resource management.
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TenantTier(str, Enum):
    """Tenant subscription tier."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TenantQuota:
    """Resource quotas for a tenant."""
    max_users: int
    max_agents: int
    max_workflows: int
    max_api_calls_per_hour: int
    max_storage_gb: int
    retention_days: int
    custom_branding: bool = False
    sso_enabled: bool = False

    @staticmethod
    def for_tier(tier: TenantTier) -> "TenantQuota":
        """Get quota for tier."""
        tiers = {
            TenantTier.STARTER: TenantQuota(
                max_users=5,
                max_agents=5,
                max_workflows=10,
                max_api_calls_per_hour=1000,
                max_storage_gb=10,
                retention_days=30,
            ),
            TenantTier.PROFESSIONAL: TenantQuota(
                max_users=50,
                max_agents=50,
                max_workflows=100,
                max_api_calls_per_hour=10000,
                max_storage_gb=100,
                retention_days=90,
                custom_branding=True,
            ),
            TenantTier.ENTERPRISE: TenantQuota(
                max_users=999999,
                max_agents=999999,
                max_workflows=999999,
                max_api_calls_per_hour=999999,
                max_storage_gb=999999,
                retention_days=365,
                custom_branding=True,
                sso_enabled=True,
            ),
        }
        return tiers.get(tier, tiers[TenantTier.STARTER])


@dataclass
class Tenant:
    """Tenant definition."""
    id: str
    name: str
    tier: TenantTier
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    quota: TenantQuota = field(default_factory=lambda: TenantQuota.for_tier(TenantTier.STARTER))
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier.value,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "quota": {
                "max_users": self.quota.max_users,
                "max_agents": self.quota.max_agents,
                "max_workflows": self.quota.max_workflows,
                "api_calls_per_hour": self.quota.max_api_calls_per_hour,
            },
        }


@dataclass
class TenantContext:
    """Context for current tenant."""
    tenant_id: str
    tenant_name: str
    user_id: str
    request_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TenantManager:
    """Manages tenants and their settings."""

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.tenant_users: Dict[str, List[str]] = {}  # tenant_id -> user_ids
        self.audit_log: List[Dict[str, Any]] = []

    async def create_tenant(
        self,
        name: str,
        tier: TenantTier = TenantTier.STARTER,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"

        tenant = Tenant(
            id=tenant_id,
            name=name,
            tier=tier,
            quota=TenantQuota.for_tier(tier),
        )

        self.tenants[tenant_id] = tenant
        self.tenant_users[tenant_id] = []

        self._audit_log("tenant_created", tenant_id, {"name": name, "tier": tier.value})
        logger.info(f"Tenant created: {tenant_id} ({name})")

        return tenant

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self.tenants.get(tenant_id)

    async def update_tenant(
        self, tenant_id: str, **updates
    ) -> Optional[Tenant]:
        """Update tenant."""
        if tenant_id not in self.tenants:
            return None

        tenant = self.tenants[tenant_id]

        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.updated_at = datetime.utcnow()

        self._audit_log("tenant_updated", tenant_id, updates)
        logger.info(f"Tenant updated: {tenant_id}")

        return tenant

    async def upgrade_tier(
        self, tenant_id: str, new_tier: TenantTier
    ) -> Optional[Tenant]:
        """Upgrade tenant tier."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return None

        tenant.tier = new_tier
        tenant.quota = TenantQuota.for_tier(new_tier)
        tenant.updated_at = datetime.utcnow()

        self._audit_log(
            "tier_upgraded",
            tenant_id,
            {"from": tenant.tier.value, "to": new_tier.value},
        )

        logger.info(f"Tenant tier upgraded: {tenant_id} -> {new_tier.value}")
        return tenant

    async def add_user(self, tenant_id: str, user_id: str) -> bool:
        """Add user to tenant."""
        if tenant_id not in self.tenant_users:
            return False

        users = self.tenant_users[tenant_id]
        if user_id not in users:
            users.append(user_id)
            self._audit_log("user_added", tenant_id, {"user_id": user_id})
            return True

        return False

    async def remove_user(self, tenant_id: str, user_id: str) -> bool:
        """Remove user from tenant."""
        if tenant_id not in self.tenant_users:
            return False

        users = self.tenant_users[tenant_id]
        if user_id in users:
            users.remove(user_id)
            self._audit_log("user_removed", tenant_id, {"user_id": user_id})
            return True

        return False

    def _audit_log(self, action: str, tenant_id: str, details: Dict[str, Any]) -> None:
        """Log audit event."""
        self.audit_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "tenant_id": tenant_id,
                "details": details,
            }
        )

    def get_audit_log(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit log."""
        if tenant_id:
            return [log for log in self.audit_log if log["tenant_id"] == tenant_id]
        return self.audit_log


class TenantContextManager:
    """Manages tenant context for requests."""

    def __init__(self):
        self.current_context: Optional[TenantContext] = None

    def set_context(self, context: TenantContext) -> None:
        """Set tenant context."""
        self.current_context = context
        logger.info(
            f"Tenant context set: {context.tenant_id} "
            f"(user: {context.user_id})"
        )

    def get_context(self) -> Optional[TenantContext]:
        """Get current tenant context."""
        return self.current_context

    def clear_context(self) -> None:
        """Clear tenant context."""
        self.current_context = None

    def ensure_context(self) -> TenantContext:
        """Ensure context is set."""
        if not self.current_context:
            raise Exception("No tenant context set")
        return self.current_context


class TenantResourceManager:
    """Manages tenant resource usage."""

    def __init__(self):
        self.usage: Dict[str, Dict[str, int]] = {}

    async def check_quota(
        self, tenant_id: str, resource_type: str, quota_manager: TenantManager
    ) -> bool:
        """Check if tenant can use more of resource."""
        tenant = await quota_manager.get_tenant(tenant_id)
        if not tenant:
            return False

        if tenant_id not in self.usage:
            self.usage[tenant_id] = {}

        current_usage = self.usage[tenant_id].get(resource_type, 0)
        quota_attr = f"max_{resource_type}"

        if hasattr(tenant.quota, quota_attr):
            quota = getattr(tenant.quota, quota_attr)
            return current_usage < quota

        return True

    async def record_usage(
        self, tenant_id: str, resource_type: str, amount: int = 1
    ) -> None:
        """Record resource usage."""
        if tenant_id not in self.usage:
            self.usage[tenant_id] = {}

        self.usage[tenant_id][resource_type] = (
            self.usage[tenant_id].get(resource_type, 0) + amount
        )

    def get_usage(self, tenant_id: str) -> Dict[str, int]:
        """Get tenant usage."""
        return self.usage.get(tenant_id, {})

    def reset_usage(self, tenant_id: str, resource_type: Optional[str] = None) -> None:
        """Reset usage counters."""
        if not tenant_id in self.usage:
            return

        if resource_type:
            self.usage[tenant_id][resource_type] = 0
        else:
            self.usage[tenant_id] = {}


class TenantIsolationMiddleware:
    """Middleware for tenant isolation."""

    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.context_manager = TenantContextManager()

    async def process_request(
        self, tenant_id: str, user_id: str, request_id: str
    ) -> TenantContext:
        """Process request and set tenant context."""
        tenant = await self.tenant_manager.get_tenant(tenant_id)
        if not tenant or not tenant.is_active:
            raise Exception(f"Tenant not found or inactive: {tenant_id}")

        context = TenantContext(
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            user_id=user_id,
            request_id=request_id,
        )

        self.context_manager.set_context(context)
        return context

    def get_current_context(self) -> TenantContext:
        """Get current request context."""
        return self.context_manager.ensure_context()

    def clear_context(self) -> None:
        """Clear context after request."""
        self.context_manager.clear_context()
