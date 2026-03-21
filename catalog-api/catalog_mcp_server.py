#!/usr/bin/env python
"""
Standalone MCP Server for Data Catalog.
Runs as a separate service that Claude Desktop can connect to.

This implements the Model Context Protocol using stdio transport,
allowing Claude Desktop to browse and query catalog assets.

Install with:
  pip install mcp

Run with:
  python catalog_mcp_server.py

Add to Claude Desktop config (~/.config/Claude/claude_desktop_config.json):
  "data-catalog": {
    "command": "python",
    "args": ["path/to/catalog_mcp_server.py"]
  }
"""

import asyncio
import json
import logging
import sys
from typing import Any

import httpx

# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Catalog API endpoint
CATALOG_API_URL = "http://localhost:8001"


class CatalogMCPServer:
    """MCP Server implementation for Data Catalog."""

    def __init__(self, base_url: str = CATALOG_API_URL):
        self.base_url = base_url
        self.client = None
        self.assets_cache = None
        self.message_id_counter = 0

    async def init(self):
        """Initialize the client."""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self):
        """Close the client."""
        if self.client:
            await self.client.aclose()

    async def list_resources(self) -> list[dict[str, Any]]:
        """List all catalog assets as MCP resources."""
        try:
            response = await self.client.get("/assets")
            response.raise_for_status()
            assets = response.json()

            resources = []
            for asset in assets:
                resources.append({
                    "uri": f"catalog://asset/{asset['id']}",
                    "name": asset.get('display_name', asset['name']),
                    "description": asset.get('description', 'No description'),
                    "mimeType": "application/json",
                })

            self.assets_cache = {a['id']: a for a in assets}
            return resources
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return []

    async def read_resource(self, uri: str) -> str:
        """Read a specific asset resource."""
        try:
            if not uri.startswith("catalog://asset/"):
                return json.dumps({"error": f"Invalid URI: {uri}"})

            asset_id = int(uri.replace("catalog://asset/", ""))
            response = await self.client.get(f"/assets/{asset_id}")
            response.raise_for_status()
            asset = response.json()

            formatted = {
                "id": asset.get('id'),
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

    async def query_asset(self, asset_id: int, question: str) -> dict:
        """Query an asset with Claude via the catalog API."""
        try:
            payload = {
                "asset_id": asset_id,
                "message": question,
                "conversation_history": []
            }

            response = await self.client.post("/ai-lab/chat", json=payload)
            response.raise_for_status()
            result = response.json()

            return result
        except Exception as e:
            logger.error(f"Failed to query asset {asset_id}: {e}")
            return {"error": str(e)}


# Global server instance
server = None


async def handle_initialize(params):
    """Handle initialize request."""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "resources": {},
            "tools": {},
        },
        "serverInfo": {
            "name": "Data Catalog MCP Server",
            "version": "1.0.0"
        }
    }


async def handle_resources_list(params):
    """Handle resources/list request."""
    resources = await server.list_resources()
    return {"resources": resources}


async def handle_resources_read(params):
    """Handle resources/read request."""
    uri = params.get("uri")
    contents = await server.read_resource(uri)
    return {
        "contents": [{
            "uri": uri,
            "mimeType": "application/json",
            "text": contents
        }]
    }


async def handle_tools_list(params):
    """Handle tools/list request."""
    tools = [
        {
            "name": "list_assets",
            "description": "List all available catalog assets with their names and descriptions.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_asset_details",
            "description": "Get detailed information about a catalog asset including columns and metadata.",
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
        },
        {
            "name": "query_asset",
            "description": "Ask a question about a specific catalog asset. Claude will generate SQL, execute it, and provide analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "The ID of the catalog asset to query"
                    },
                    "question": {
                        "type": "string",
                        "description": "Natural language question about the asset data (e.g., 'What are the top 5 incident priorities?')"
                    }
                },
                "required": ["asset_id", "question"]
            }
        }
    ]
    return {"tools": tools}


async def handle_tools_call(params):
    """Handle tools/call request."""
    tool_name = params.get("name")
    tool_input = params.get("arguments", {})

    try:
        if tool_name == "list_assets":
            resources = await server.list_resources()
            content = json.dumps(resources, indent=2, default=str)

        elif tool_name == "get_asset_details":
            asset_id = tool_input.get("asset_id")
            uri = f"catalog://asset/{asset_id}"
            content = await server.read_resource(uri)

        elif tool_name == "query_asset":
            asset_id = tool_input.get("asset_id")
            question = tool_input.get("question")
            result = await server.query_asset(asset_id, question)
            content = json.dumps(result, indent=2, default=str)

        else:
            content = json.dumps({"error": f"Unknown tool: {tool_name}"})

        return {
            "content": [{
                "type": "text",
                "text": content
            }]
        }

    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": str(e)})
            }]
        }


async def handle_message(message: dict):
    """Handle incoming MCP message."""
    method = message.get("method")
    params = message.get("params", {})
    msg_id = message.get("id")
    
    # Check if this is a notification (no id) or a request (has id)
    is_notification = msg_id is None

    logger.info(f"Received: {method}")

    try:
        if method == "initialize":
            result = await handle_initialize(params)
        elif method == "resources/list":
            result = await handle_resources_list(params)
        elif method == "resources/read":
            result = await handle_resources_read(params)
        elif method == "tools/list":
            result = await handle_tools_list(params)
        elif method == "tools/call":
            result = await handle_tools_call(params)
        elif method == "notifications/initialized":
            # Notifications don't get responses
            logger.info("Server initialized successfully")
            return None
        else:
            result = {"error": f"Unknown method: {method}"}

        # Only send response for requests, not notifications
        if not is_notification:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
            return response
        else:
            # Notification received, no response needed
            return None
            
    except Exception as e:
        logger.error(f"Error handling {method}: {e}", exc_info=True)
        
        # Only send error response for requests, not notifications
        if not is_notification:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            return response
        else:
            return None


async def main():
    """Main event loop for the MCP server."""
    global server
    
    server = CatalogMCPServer()
    await server.init()

    logger.info("Data Catalog MCP Server started")
    logger.info(f"Connecting to catalog API at {CATALOG_API_URL}")

    try:
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                message = json.loads(line)
                response = await handle_message(message)
                
                # Only send response if it exists (requests have responses, notifications don't)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)

    finally:
        await server.close()
        logger.info("Data Catalog MCP Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
