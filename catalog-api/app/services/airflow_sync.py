"""Service to poll Airflow REST API for DAG run status and update asset freshness."""

import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import get_settings
from app.models.asset import CatalogAsset, PipelineStatusEnum

logger = logging.getLogger(__name__)

# Map Airflow DAG state to pipeline status
STATE_TO_STATUS = {
    "success": PipelineStatusEnum.HEALTHY,
    "failed": PipelineStatusEnum.WARNING,
    "queued": PipelineStatusEnum.HEALTHY,
    "running": PipelineStatusEnum.HEALTHY,
    "upstream_failed": PipelineStatusEnum.WARNING,
}


class AirflowSyncError(Exception):
    """Raised when Airflow sync fails."""
    pass


class AirflowSync:
    """Poll Airflow REST API for DAG status and update catalog assets."""

    @staticmethod
    async def get_last_dag_run(dag_id: str) -> Optional[dict]:
        """
        Fetch the last DAG run from Airflow REST API.

        Args:
            dag_id: Airflow DAG ID

        Returns:
            Dict with dag_run status/execution_date, or None if not found

        Raises:
            AirflowSyncError: If API call fails
        """
        settings = get_settings()
        url = f"{settings.airflow_api_url}/dags/{dag_id}/dagRuns"
        
        params = {"limit": 1, "state": ["success", "failed"]}

        try:
            async with httpx.AsyncClient(
                auth=(settings.airflow_admin_user, settings.airflow_admin_pass),
                timeout=10.0
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                dag_runs = data.get("dag_runs", [])

                if dag_runs:
                    run = dag_runs[0]
                    return {
                        "state": run.get("state", "unknown"),
                        "execution_date": run.get("execution_date"),
                        "end_date": run.get("end_date")
                    }
                return None
        except httpx.HTTPError as e:
            raise AirflowSyncError(f"Airflow API error: {str(e)}")
        except Exception as e:
            raise AirflowSyncError(f"Unexpected error fetching DAG run: {str(e)}")

    @staticmethod
    async def sync_asset_status(
        asset: CatalogAsset, session: AsyncSession
    ) -> bool:
        """
        Update asset's pipeline_status and last_synced_at based on DAG run.

        Args:
            asset: CatalogAsset to update (must have airflow_dag_id)
            session: AsyncSession for database updates

        Returns:
            True if successfully updated, False if no DAG found or asset has no airflow_dag_id
        """
        if not asset.airflow_dag_id:
            logger.info(f"Asset {asset.name} has no airflow_dag_id, skipping sync")
            return False

        try:
            dag_run = await AirflowSync.get_last_dag_run(asset.airflow_dag_id)
            if not dag_run:
                logger.info(f"No recent DAG run found for {asset.airflow_dag_id}")
                return False

            # Map state to pipeline status
            state = dag_run.get("state", "unknown").lower()
            new_status = STATE_TO_STATUS.get(state, PipelineStatusEnum.UNKNOWN)

            # Update asset
            stmt = (
                update(CatalogAsset)
                .where(CatalogAsset.id == asset.id)
                .values(
                    pipeline_status=new_status,
                    last_synced_at=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()

            logger.info(
                f"Updated {asset.name}: status={new_status}, "
                f"last_synced={dag_run.get('execution_date')}"
            )
            return True
        except AirflowSyncError as e:
            logger.warning(f"Failed to sync asset {asset.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error syncing asset {asset.name}: {e}")
            return False

    @staticmethod
    async def sync_all_assets(session: AsyncSession) -> dict:
        """
        Sync all assets with Airflow DAG status.

        Args:
            session: AsyncSession for database operations

        Returns:
            Dict with sync statistics (updated, skipped, failed)
        """
        # Fetch all assets
        result = await session.execute(select(CatalogAsset))
        assets = result.scalars().all()

        stats = {"updated": 0, "skipped": 0, "failed": 0}

        for asset in assets:
            try:
                success = await AirflowSync.sync_asset_status(asset, session)
                if success:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Error syncing asset {asset.name}: {e}")
                stats["failed"] += 1

        logger.info(f"Airflow sync complete: {stats}")
        return stats
