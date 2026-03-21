"""
Model Context Protocol (MCP) Server for Data Catalog.
Enables Claude Desktop to browse and query catalog assets.

Implements:
- Resource listing: Browse all catalog assets
- Resource read: Get asset details with columns
- Tools: Query assets with Claude
"""

import json
import logging
from typing import Any
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Catalog API endpoint
CATALOG_API_URL = "http://localhost:8001"


class CatalogMCPServer:
    """MCP Server for Data Catalog integration with Claude Desktop."""

    def __init__(self, base_url: str = CATALOG_API_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)

    async def list_resources(self) -> list[dict[str, Any]]:
        """List all catalog assets as MCP resources."""
        try:
            response = self.client.get("/assets")
            response.raise_for_status()
            assets = response.json()
            
            resources = []
            for asset in assets:
                resources.append({
                    "uri": f"catalog://asset/{asset['id']}",
                    "name": asset.get('display_name', asset['name']),
                    "description": asset.get('description', ''),
                    "mimeType": "application/json",
                })
            
            return resources
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return []

    async def read_resource(self, uri: str) -> str:
        """Read a specific asset resource (returns full asset details)."""
        try:
            # Parse URI: catalog://asset/{id}
            if not uri.startswith("catalog://asset/"):
                return json.dumps({"error": f"Invalid URI: {uri}"})
            
            asset_id = uri.replace("catalog://asset/", "")
            response = self.client.get(f"/assets/{asset_id}")
            response.raise_for_status()
            asset = response.json()
            
            # Format nicely for Claude
            formatted = {
                "name": asset.get('name'),
                "displayName": asset.get('display_name'),
                "description": asset.get('description'),
                "schema": asset.get('schema_name'),
                "table": asset.get('table_name'),
                "database": asset.get('database'),
                "owner": asset.get('owner'),
                "tags": asset.get('tags', []),
                "columns": asset.get('columns', []),
                "rowCount": asset.get('row_count'),
                "pipelineStatus": asset.get('pipeline_status'),
            }
            
            return json.dumps(formatted, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to read resource {uri}: {e}")
            return json.dumps({"error": str(e)})

    async def query_asset(self, asset_id: int, question: str, conversation_history: list = None) -> dict:
        """
        Query an asset with Claude.
        
        Args:
            asset_id: Catalog asset ID
            question: Natural language question about the asset
            conversation_history: Previous conversation messages
        
        Returns:
            Claude response with SQL query and results
        """
        try:
            payload = {
                "asset_id": asset_id,
                "message": question,
                "conversation_history": conversation_history or []
            }
            
            response = self.client.post("/ai-lab/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            
            return {
                "question": question,
                "response": result.get('response'),
                "query": result.get('query'),
                "results": result.get('results'),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to query asset {asset_id}: {e}")
            return {"error": str(e)}

    def get_tools(self) -> list[dict]:
        """Return MCP tool definitions for Claude."""
        return [
            {
                "name": "query_catalog_asset",
                "description": "Ask Claude a question about a specific catalog asset. Claude will generate SQL, execute it, and provide insights.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "asset_id": {
                            "type": "integer",
                            "description": "The ID of the catalog asset to query"
                        },
                        "question": {
                            "type": "string",
                            "description": "Natural language question about the asset (e.g., 'How many incidents are open?')"
                        }
                    },
                    "required": ["asset_id", "question"]
                }
            },
            {
                "name": "list_catalog_assets",
                "description": "List all available catalog assets with their names and descriptions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_asset_details",
                "description": "Get detailed information about a catalog asset including all columns and metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "asset_id": {
                            "type": "integer",
                            "description": "The ID of the catalog asset"
                        }
                    },
                    "required": ["asset_id"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Handle tool calls from Claude."""
        try:
            if tool_name == "list_catalog_assets":
                resources = await self.list_resources()
                return json.dumps(resources, indent=2)
            
            elif tool_name == "get_asset_details":
                asset_id = tool_input.get("asset_id")
                uri = f"catalog://asset/{asset_id}"
                return await self.read_resource(uri)
            
            elif tool_name == "query_catalog_asset":
                asset_id = tool_input.get("asset_id")
                question = tool_input.get("question")
                result = await self.query_asset(asset_id, question)
                return json.dumps(result, indent=2, default=str)
            
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return json.dumps({"error": str(e)})


# Singleton instance
_server_instance = None


def get_catalog_mcp_server() -> CatalogMCPServer:
    """Get or create the catalog MCP server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = CatalogMCPServer()
    return _server_instance
