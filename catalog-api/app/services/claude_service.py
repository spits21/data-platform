"""Claude AI integration service with tool use for SQL execution."""

import json
import logging
from typing import Optional, List, Dict, Any
from anthropic import AsyncAnthropic

from app.config import get_settings
from app.models.asset import CatalogAsset
from app.services.sql_executor import SQLExecutor

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 10  # Prevent infinite loops


class ClaudeService:
    """Manage Claude API integration with tool use."""

    def __init__(self):
        """Initialize Anthropic client."""
        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _build_system_prompt(self, asset: CatalogAsset) -> str:
        """Build system prompt with asset context."""
        columns_text = ""
        if asset.columns and isinstance(asset.columns, list):
            for col in asset.columns:
                col_name = col.get("name", "?")
                col_type = col.get("type", "?")
                col_desc = col.get("description", "")
                col_tags = col.get("ai_tags", [])
                tags_str = f" [{', '.join(col_tags)}]" if col_tags else ""
                columns_text += f"    {col_name} ({col_type}){tags_str}"
                if col_desc:
                    columns_text += f" — {col_desc}"
                columns_text += "\n"

        return f"""You have read-only access to the following PostgreSQL table:

Database : {asset.database}
Schema   : {asset.schema_name}
Table    : {asset.table_name}
Source   : {asset.source_system.value}

Columns:
{columns_text or "  (no metadata available)"}

Data context:
  Rows         : ~{asset.row_count or '?'}
  Last synced  : {asset.last_synced_at or 'unknown'}
  dbt model    : {asset.dbt_model_name or 'N/A'}
  Airflow DAG  : {asset.airflow_dag_id or 'N/A'}

Answer the user's question. Use run_sql when you need data.
Always qualify table names: {asset.schema_name}.{asset.table_name}
Format numbers clearly. Be concise."""

    def _get_tool_definition(self, asset: CatalogAsset) -> Dict[str, Any]:
        """Define run_sql tool for Claude."""
        return {
            "name": "run_sql",
            "description": (
                f"Execute a READ-ONLY SELECT query against "
                f"{asset.schema_name}.{asset.table_name} in local PostgreSQL. "
                f"Always use schema-qualified names. Never use INSERT, UPDATE, DELETE, DROP, or DDL."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT statement"
                    }
                },
                "required": ["query"]
            }
        }

    async def chat(
        self,
        asset: CatalogAsset,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> tuple[str, List[str]]:
        """
        Chat with Claude about an asset with tool use enabled.

        Args:
            asset: CatalogAsset to query
            user_message: User's question
            conversation_history: Previous messages (role/content dicts)

        Returns:
            Tuple of (final_response_text, list_of_executed_sql_statements)
        """
        system_prompt = self._build_system_prompt(asset)
        tool_def = self._get_tool_definition(asset)
        executed_sql = []

        # Build initial messages
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_message})

        # Agentic loop
        for turn in range(MAX_TURNS):
            logger.info(f"Claude turn {turn + 1}/{MAX_TURNS}")

            # Call Claude with tool_choice enabled
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_prompt,
                tools=[tool_def],
                messages=messages
            )

            # Add assistant response to history (convert content blocks to dicts)
            content_list = []
            for block in response.content:
                if hasattr(block, "text"):
                    content_list.append({"type": "text", "text": block.text})
                elif hasattr(block, "name"):  # tool_use block
                    content_list.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            messages.append({
                "role": "assistant",
                "content": content_list
            })

            # Check for tool use
            tool_results_to_send = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    if tool_name == "run_sql":
                        query = tool_input.get("query", "")
                        logger.info(f"Claude requested SQL: {query[:100]}...")

                        try:
                            results = await SQLExecutor.execute(query, asset)
                            executed_sql.append(query)
                            logger.info(f"Query returned {len(results)} rows")

                            tool_results_to_send.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(results[:50])  # Send first 50 rows
                            })
                        except Exception as e:
                            tool_results_to_send.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Error: {str(e)}",
                                "is_error": True
                            })

            # If tools were used, send results and continue loop
            if tool_results_to_send:
                messages.append({
                    "role": "user",
                    "content": tool_results_to_send
                })
                continue

            # No more tool use → extract final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            logger.info(f"Conversation complete after {turn + 1} turns")
            return final_text, executed_sql

        # Max turns reached
        logger.warning(f"Max turns ({MAX_TURNS}) reached")
        return "Conversation exceeded maximum turns.", executed_sql
