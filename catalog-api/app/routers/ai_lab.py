"""Router for Claude AI Lab chat endpoint."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import DatabaseManager
from app.models.asset import CatalogAsset
from app.schemas.asset import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService
from app.services.auth_service import get_current_user, check_asset_access

router = APIRouter(prefix="/ai-lab", tags=["ai-lab"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
):
    """Chat with Claude about a catalog asset. Requires auth and asset access."""
    result = await session.execute(select(CatalogAsset).where(CatalogAsset.id == request.asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await check_asset_access(user, asset.table_name)

    claude_service = ClaudeService()

    history = []
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    try:
        response_text, executed_sql = await claude_service.chat(
            asset=asset,
            user_message=request.message,
            conversation_history=history,
        )
        return ChatResponse(
            response=response_text,
            sql_executed=executed_sql,
            asset_id=request.asset_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
