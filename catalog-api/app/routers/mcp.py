"""Router for MCP server endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.database import DatabaseManager
from app.models.asset import CatalogAsset
from app.services.auth_service import get_current_user, check_asset_access

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/asset/{asset_id}")
async def get_asset_mcp(
    asset_id: int,
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return MCP-compatible manifest for an asset.
    Requires authentication and validates application role access.
    """
    result = await session.execute(select(CatalogAsset).where(CatalogAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await check_asset_access(user, asset.table_name)

    table_name = asset.table_name
    qualified_table = f"{asset.schema_name}.{asset.table_name}"

    tools = [
        {
            "name": f"query_{table_name}",
            "description": f"Execute a SELECT query against {qualified_table}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL SELECT statement (read-only)"
                    }
                },
                "required": ["sql"]
            }
        },
        {
            "name": "get_schema",
            "description": f"Get column metadata for {qualified_table}",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_lineage",
            "description": f"Get data lineage for {qualified_table} (dbt model + source)",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]

    return {
        "protocolVersion": "2024-11-05",
        "name": f"catalog_asset_{asset_id}",
        "description": asset.display_name,
        "version": "1.0.0",
        "resources": [
            {
                "uri": f"asset://{asset_id}",
                "name": asset.name,
                "description": asset.description or "",
                "mimeType": "application/vnd.catalog+json"
            }
        ],
        "tools": tools
    }
