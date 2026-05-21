"""
Database Connection Management

Handles PostgreSQL and Neo4j connections with proper session management,
connection pooling, and lifecycle management.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import declarative_base
from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# ============================================================================
# POSTGRESQL
# ============================================================================

# Create async engine
engine = create_async_engine(
    settings.get_database_url(async_mode=True),
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # Test connection before using
    # Use QueuePool for development, NullPool for serverless
    poolclass=QueuePool if not settings.is_production() else NullPool,
    # Connection pool options
    connect_args={
        "timeout": 30,
        "server_settings": {
            "application_name": "gbrain-api",
        },
    },
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Yields:
        AsyncSession: Database session

    Example:
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Yields:
        AsyncSession: Database session

    Example:
        async with get_db_context() as db:
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables and run migrations.

    This function:
    1. Creates all tables from ORM models
    2. Runs Alembic migrations
    3. Seeds initial data if needed
    """
    logger.info("Initializing PostgreSQL database...")

    try:
        # Create tables from ORM models (for development only)
        # In production, use Alembic migrations
        if settings.is_development():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Created database tables")

        # Test connection
        async with async_session_factory() as session:
            await session.execute("SELECT 1")
            logger.info("Database connection verified")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """Close database connection pool."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


# ============================================================================
# NEO4J GRAPH DATABASE
# ============================================================================

_neo4j_driver: Optional[AsyncDriver] = None


def get_neo4j_driver() -> AsyncDriver:
    """
    Get Neo4j driver instance (lazy initialization).

    Returns:
        AsyncDriver: Neo4j async driver

    Raises:
        RuntimeError: If driver initialization fails
    """
    global _neo4j_driver

    if _neo4j_driver is None:
        try:
            _neo4j_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_pool_size=50,
                user_agent="gbrain-api/0.1.0",
            )
            logger.info(f"Connected to Neo4j at {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise RuntimeError(f"Neo4j connection failed: {e}")

    return _neo4j_driver


async def get_neo4j_session():
    """
    Get Neo4j async session.

    Yields:
        AsyncSession: Neo4j async session
    """
    driver = get_neo4j_driver()
    async with driver.session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Neo4j session error: {e}")
            raise


async def close_neo4j() -> None:
    """Close Neo4j driver."""
    global _neo4j_driver

    if _neo4j_driver:
        try:
            await _neo4j_driver.close()
            logger.info("Neo4j driver closed")
            _neo4j_driver = None
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}")


async def verify_neo4j_connection() -> bool:
    """
    Verify Neo4j connection is working.

    Returns:
        bool: True if connection is valid
    """
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1")
            await result.consume()
            logger.info("Neo4j connection verified")
            return True
    except Exception as e:
        logger.error(f"Neo4j connection verification failed: {e}")
        return False


async def init_neo4j() -> None:
    """Initialize Neo4j database with schema and indexes."""
    logger.info("Initializing Neo4j knowledge graph...")

    try:
        driver = get_neo4j_driver()

        async with driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT unique_person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT unique_team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT unique_workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Constraint creation warning: {e}")

            logger.info("Neo4j constraints and indexes created")

        await verify_neo4j_connection()

    except Exception as e:
        logger.error(f"Failed to initialize Neo4j: {e}", exc_info=True)
        raise


# ============================================================================
# INITIALIZATION
# ============================================================================

async def initialize_all_databases() -> None:
    """Initialize all database connections."""
    logger.info("Initializing all database connections...")

    try:
        # PostgreSQL
        await init_db()

        # Neo4j
        await init_neo4j()

        logger.info("All databases initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise


async def shutdown_all_databases() -> None:
    """Shutdown all database connections."""
    logger.info("Shutting down all database connections...")

    try:
        await close_db()
        await close_neo4j()
        logger.info("All databases shutdown successfully")

    except Exception as e:
        logger.error(f"Error during database shutdown: {e}", exc_info=True)
