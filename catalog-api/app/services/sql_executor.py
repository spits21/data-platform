"""Safe read-only SQL executor for Claude's run_sql tool."""

import re
import logging
from typing import List, Dict, Any

from app.itsm_reader import ITSMReader
from app.models.asset import CatalogAsset

logger = logging.getLogger(__name__)

# Keywords that indicate write/DDL operations (forbidden)
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "CREATE", "ALTER", "GRANT", "REVOKE"
}

MAX_ROWS = 500
DEFAULT_LIMIT = 500


class SQLExecutionError(Exception):
    """Raised when SQL validation or execution fails."""
    pass


class SQLExecutor:
    """Validate and execute read-only SELECT queries."""

    @staticmethod
    def validate_sql(query: str, asset: CatalogAsset) -> None:
        """
        Validate SQL query for safety before execution.

        Args:
            query: SQL query string
            asset: CatalogAsset being queried (to check table name)

        Raises:
            SQLExecutionError: If query fails safety checks
        """
        # Rule 1: Strip and check it starts with SELECT
        stripped = query.strip()
        if not stripped.upper().startswith("SELECT"):
            raise SQLExecutionError("Query must start with SELECT")

        # Rule 2: Reject forbidden keywords (case-insensitive)
        normalized = stripped.upper()
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in normalized:
                raise SQLExecutionError(
                    f"Query contains forbidden keyword: {keyword}"
                )

        # Rule 3: Table name must appear in query
        if asset.table_name.upper() not in normalized:
            raise SQLExecutionError(
                f"Query must reference table: {asset.table_name}"
            )

        logger.info(f"Query validation passed for {asset.table_name}")

    @staticmethod
    def add_limit(query: str) -> str:
        """
        Append LIMIT clause if not present.

        Args:
            query: SQL query

        Returns:
            Query with LIMIT clause appended (if needed)
        """
        # Check if LIMIT already present (case-insensitive)
        if re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
            return query

        # Append limit
        return f"{query.strip()} LIMIT {DEFAULT_LIMIT}"

    @classmethod
    async def execute(
        cls, query: str, asset: CatalogAsset
    ) -> List[Dict[str, Any]]:
        """
        Execute validated read-only query and return results.

        Args:
            query: SQL SELECT query
            asset: CatalogAsset (for validation)

        Returns:
            List of result dictionaries (max 500 rows)

        Raises:
            SQLExecutionError: If validation or execution fails
        """
        # Validate
        cls.validate_sql(query, asset)

        # Add LIMIT if missing (Rule 4)
        safe_query = cls.add_limit(query)

        try:
            # Execute via asyncpg read-only connection (Rule 5)
            results = await ITSMReader.execute_read_only(safe_query)

            # Rule 6: Return max 500 rows
            return results[:MAX_ROWS]
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise SQLExecutionError(f"Query execution failed: {str(e)}")
