"""Router for catalog asset CRUD operations."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import DatabaseManager
from app.models.asset import CatalogAsset
from app.schemas.asset import AssetCreate, AssetRead
from app.services.auth_service import get_current_user, check_asset_access

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
async def list_assets(
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
):
    """List all catalog assets. Requires authentication."""
    result = await session.execute(select(CatalogAsset))
    assets = result.scalars().all()
    return assets


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(
    asset_id: int,
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
):
    """Get a single asset by ID. Validates application role access."""
    result = await session.execute(select(CatalogAsset).where(CatalogAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await check_asset_access(user, asset.table_name)
    return asset


@router.post("", response_model=AssetRead, status_code=201)
async def create_asset(
    asset_create: AssetCreate,
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
):
    """Create a new catalog asset. Requires authentication."""
    result = await session.execute(select(CatalogAsset).where(CatalogAsset.name == asset_create.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Asset name already exists")

    db_asset = CatalogAsset(
        name=asset_create.name,
        display_name=asset_create.display_name,
        description=asset_create.description,
        schema_name=asset_create.schema_name,
        table_name=asset_create.table_name,
        database="airflow",
        source_system=asset_create.source_system,
        columns=[col.model_dump() for col in (asset_create.columns or [])],
        tags=asset_create.tags or [],
        owner=asset_create.owner,
        row_count=asset_create.row_count,
        pipeline_status=asset_create.pipeline_status,
        dbt_model_name=asset_create.dbt_model_name,
        airflow_dag_id=asset_create.airflow_dag_id,
    )

    session.add(db_asset)
    await session.commit()
    await session.refresh(db_asset)
    return db_asset


@router.put("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int,
    asset_update: AssetCreate,
    session: AsyncSession = Depends(DatabaseManager.get_session),
    user: dict = Depends(get_current_user),
):
    """Update an existing asset. Requires authentication."""
    result = await session.execute(select(CatalogAsset).where(CatalogAsset.id == asset_id))
    db_asset = result.scalar_one_or_none()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db_asset.display_name = asset_update.display_name
    db_asset.description = asset_update.description
    db_asset.schema_name = asset_update.schema_name
    db_asset.table_name = asset_update.table_name
    db_asset.source_system = asset_update.source_system
    db_asset.columns = [col.model_dump() for col in (asset_update.columns or [])]
    db_asset.tags = asset_update.tags or []
    db_asset.owner = asset_update.owner
    db_asset.row_count = asset_update.row_count
    db_asset.pipeline_status = asset_update.pipeline_status
    db_asset.dbt_model_name = asset_update.dbt_model_name
    db_asset.airflow_dag_id = asset_update.airflow_dag_id

    await session.commit()
    await session.refresh(db_asset)
    return db_asset
