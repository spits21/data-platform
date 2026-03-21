"""Read-only asyncpg pool for querying airflow database (not using SQLAlchemy)."""

import asyncpg
import logging
from typing import List, Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class ITSMReader:
    """Manage asyncpg connection pool for read-only queries to airflow database."""

    _pool: asyncpg.Pool | None = None

    @classmethod
    async def initialize(cls) -> None:
        """Create asyncpg connection pool targeting airflow database."""
        settings = get_settings()

        cls._pool = await asyncpg.create_pool(
            settings.asyncpg_airflow_dsn,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("ITSM reader pool initialized")

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        """Get asyncpg connection pool."""
        if cls._pool is None:
            raise RuntimeError("ITSM reader not initialized. Call initialize() first.")
        return cls._pool

    @classmethod
    async def execute_read_only(cls, query: str) -> List[Dict[str, Any]]:
        """
        Execute a read-only SELECT query and return results as list of dicts.

        Args:
            query: SQL SELECT statement (must start with SELECT when stripped)

        Returns:
            List of dictionaries mapping column names to values
        """
        pool = cls.get_pool()

        async with pool.acquire() as conn:
            # Set transaction to read-only for safety
            async with conn.transaction(readonly=True):
                try:
                    rows = await conn.fetch(query)
                    # asyncpg returns Record objects; convert to dicts
                    return [dict(row) for row in rows]
                except Exception as e:
                    logger.error(f"Query execution failed: {e}")
                    raise

    @classmethod
    async def close(cls) -> None:
        """Close the asyncpg pool."""
        if cls._pool:
            await cls._pool.close()
            logger.info("ITSM reader pool closed")
