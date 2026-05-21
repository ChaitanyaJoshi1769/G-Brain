"""
G-Brain Configuration Management

Loads and validates environment variables for the application.
Uses Pydantic for type-safe configuration with proper validation.
"""

from typing import Optional, List
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application configuration.

    Configuration is loaded from environment variables with support for .env files.
    """

    # =========================================================================
    # APPLICATION
    # =========================================================================

    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )

    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    API_VERSION: str = Field(
        default="0.1.0",
        description="API version",
    )

    API_HOST: str = Field(
        default="0.0.0.0",
        description="API server host",
    )

    API_PORT: int = Field(
        default=8000,
        description="API server port",
    )

    API_WORKERS: int = Field(
        default=4,
        description="Number of worker processes",
    )

    API_ROOT_PATH: str = Field(
        default="",
        description="Root path for API routes",
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://gbrain_user:gbrain_password@localhost:5432/gbrain",
        description="PostgreSQL connection URL",
    )

    DATABASE_POOL_SIZE: int = Field(
        default=20,
        description="Database connection pool size",
    )

    DATABASE_POOL_RECYCLE: int = Field(
        default=3600,
        description="Database connection recycle time in seconds",
    )

    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries to logs",
    )

    # =========================================================================
    # NEO4J GRAPH DATABASE
    # =========================================================================

    NEO4J_URI: str = Field(
        default="neo4j://localhost:7687",
        description="Neo4j connection URI",
    )

    NEO4J_USER: str = Field(
        default="neo4j",
        description="Neo4j username",
    )

    NEO4J_PASSWORD: str = Field(
        default="gbrain_password",
        description="Neo4j password",
    )

    # =========================================================================
    # REDIS CACHE
    # =========================================================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )

    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        description="Redis password",
    )

    REDIS_DB: int = Field(
        default=0,
        description="Redis database number",
    )

    # =========================================================================
    # QDRANT VECTOR DATABASE
    # =========================================================================

    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
    )

    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key",
    )

    # =========================================================================
    # S3 / OBJECT STORAGE
    # =========================================================================

    AWS_ACCESS_KEY_ID: str = Field(
        default="gbrain_admin",
        description="AWS access key ID",
    )

    AWS_SECRET_ACCESS_KEY: str = Field(
        default="gbrain_password",
        description="AWS secret access key",
    )

    S3_ENDPOINT: str = Field(
        default="http://localhost:9000",
        description="S3 endpoint URL (for MinIO in dev)",
    )

    S3_BUCKET: str = Field(
        default="gbrain-documents",
        description="S3 bucket name",
    )

    S3_REGION: str = Field(
        default="us-east-1",
        description="AWS region",
    )

    # =========================================================================
    # AUTHENTICATION & SECURITY
    # =========================================================================

    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing",
    )

    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration in minutes",
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days",
    )

    # OAuth/OIDC Configuration
    AUTH0_DOMAIN: Optional[str] = Field(
        default=None,
        description="Auth0 domain",
    )

    AUTH0_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Auth0 client ID",
    )

    AUTH0_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Auth0 client secret",
    )

    # =========================================================================
    # CORS & SECURITY
    # =========================================================================

    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ],
        description="CORS allowed origins",
    )

    CORS_CREDENTIALS: bool = Field(
        default=True,
        description="Allow CORS credentials",
    )

    CORS_METHODS: List[str] = Field(
        default=["*"],
        description="CORS allowed methods",
    )

    CORS_HEADERS: List[str] = Field(
        default=["*"],
        description="CORS allowed headers",
    )

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable rate limiting",
    )

    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        description="Rate limit requests per window",
    )

    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )

    # =========================================================================
    # LLM PROVIDERS
    # =========================================================================

    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key",
    )

    OPENAI_ORG_ID: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID",
    )

    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key",
    )

    # =========================================================================
    # CELERY / TASK QUEUE
    # =========================================================================

    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL",
    )

    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL",
    )

    CELERY_TASK_TIME_LIMIT: int = Field(
        default=3600,
        description="Task time limit in seconds",
    )

    # =========================================================================
    # OBSERVABILITY
    # =========================================================================

    ENABLE_TRACING: bool = Field(
        default=False,
        description="Enable distributed tracing",
    )

    ENABLE_METRICS: bool = Field(
        default=False,
        description="Enable metrics collection",
    )

    JAEGER_AGENT_HOST: str = Field(
        default="localhost",
        description="Jaeger agent host",
    )

    JAEGER_AGENT_PORT: int = Field(
        default=6831,
        description="Jaeger agent port",
    )

    # =========================================================================
    # FEATURES
    # =========================================================================

    ENABLE_SKILL_EXTRACTION: bool = Field(
        default=True,
        description="Enable automatic skill extraction",
    )

    ENABLE_GRAPH_INFERENCE: bool = Field(
        default=True,
        description="Enable graph relationship inference",
    )

    ENABLE_AGENT_EXECUTION: bool = Field(
        default=True,
        description="Enable autonomous agent execution",
    )

    ENABLE_APPROVALS: bool = Field(
        default=True,
        description="Enable approval workflows",
    )

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    MAX_DOCUMENT_SIZE_MB: int = Field(
        default=100,
        description="Maximum document size in MB",
    )

    MAX_CHUNK_SIZE: int = Field(
        default=1000,
        description="Maximum chunk size in tokens",
    )

    MAX_CONCURRENT_INGESTIONS: int = Field(
        default=10,
        description="Maximum concurrent ingestions",
    )

    MAX_SKILL_EXECUTION_TIME_SECONDS: int = Field(
        default=300,
        description="Maximum skill execution time in seconds",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self, async_mode: bool = True) -> str:
        """
        Get database URL with optional async mode.

        Args:
            async_mode: Use async driver if True

        Returns:
            Database connection URL
        """
        if async_mode and "asyncpg" not in self.DATABASE_URL:
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        return self.DATABASE_URL

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT


# Create global settings instance
settings = Settings()
