"""Async SQLAlchemy database setup for catalog_db."""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import text, event
import asyncpg
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage async SQLAlchemy connection pool and catalog database."""

    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker | None = None

    @classmethod
    async def initialize(cls) -> None:
        """Initialize database: create engine and ensure catalog_db exists."""
        settings = get_settings()

        # Use raw asyncpg to create catalog_db (CREATE DATABASE can't run in transaction)
        try:
            system_conn = await asyncpg.connect(
                host=settings.local_pg_host,
                port=settings.local_pg_port,
                user=settings.local_pg_user,
                password=settings.local_pg_pass,
                database="postgres"
            )
            try:
                await system_conn.execute(
                    f"CREATE DATABASE {settings.catalog_db_name}"
                )
                logger.info(f"Created new database: {settings.catalog_db_name}")
            except asyncpg.PostgresError as e:
                if "already exists" in str(e):
                    logger.debug(f"Database {settings.catalog_db_name} already exists, skipping creation")
                else:
                    raise
            finally:
                await system_conn.close()
        except Exception as e:
            logger.error(f"Failed to ensure catalog database exists: {e}")
            raise

        # Now create main engine targeting catalog_db
        cls._engine = create_async_engine(
            settings.catalog_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

        cls._session_factory = async_sessionmaker(
            cls._engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info("Database manager initialized")

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """Get async SQLAlchemy engine."""
        if cls._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker:
        """Get async session factory."""
        if cls._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls._session_factory

    @classmethod
    async def get_session(cls) -> AsyncSession:
        """Create a new async session."""
        factory = cls.get_session_factory()
        async with factory() as session:
            yield session

    @classmethod
    async def close(cls) -> None:
        """Close engine and dispose of connections."""
        if cls._engine:
            await cls._engine.dispose()
            logger.info("Database engine disposed")
