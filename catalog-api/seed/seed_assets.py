"""Seed script to populate initial catalog assets from dbt schema."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import CatalogAsset, SourceSystemEnum, PipelineStatusEnum

logger = logging.getLogger(__name__)


async def seed_catalog_assets(session: AsyncSession) -> None:
    """
    Seed catalog database with 3 initial assets from dbt project.
    
    Assets:
      1. stg_servicenow_incidents (staging, supabase source)
      2. stg_servicenow_configuration_items (staging, supabase source)
      3. incidents_with_configuration_items (marts, dbt source)
    """
    # Asset 1: stg_servicenow_incidents
    asset1 = CatalogAsset(
        name="stg_servicenow_incidents",
        display_name="ServiceNow Incidents (Staging)",
        description="Cleaned incidents sourced from Supabase",
        schema_name="staging",
        table_name="stg_servicenow_incidents",
        database="airflow",
        source_system=SourceSystemEnum.SUPABASE,
        columns=[
            {
                "name": "incident_id",
                "type": "uuid",
                "description": "Primary key",
                "ai_tags": ["join_key", "dedup"]
            },
            {
                "name": "incident_number",
                "type": "text",
                "description": "Incident number",
                "ai_tags": ["display_key"]
            },
            {
                "name": "ci_id",
                "type": "uuid",
                "description": "Foreign key to configuration items",
                "ai_tags": ["join_key", "routing"]
            },
            {
                "name": "state",
                "type": "text",
                "description": "Incident state",
                "ai_tags": ["label", "workflow", "predict"]
            },
            {
                "name": "created_at",
                "type": "timestamp",
                "description": "Creation timestamp",
                "ai_tags": ["time_series", "SLA"]
            },
        ],
        tags=["servicenow", "incident", "staging"],
        owner="data-platform",
        row_count=None,
        pipeline_status=PipelineStatusEnum.UNKNOWN,
        dbt_model_name="stg_servicenow_incidents",
        airflow_dag_id="snow_incident_sync"
    )

    # Asset 2: stg_servicenow_configuration_items
    asset2 = CatalogAsset(
        name="stg_servicenow_configuration_items",
        display_name="ServiceNow Configuration Items (Staging)",
        description="Cleaned configuration items sourced from Supabase",
        schema_name="staging",
        table_name="stg_servicenow_configuration_items",
        database="airflow",
        source_system=SourceSystemEnum.SUPABASE,
        columns=[
            {
                "name": "record_id",
                "type": "uuid",
                "description": "Primary key",
                "ai_tags": ["join_key", "dedup"]
            },
            {
                "name": "record_name",
                "type": "text",
                "description": "Configuration item name",
                "ai_tags": ["NLP", "embedding", "RAG"]
            },
            {
                "name": "created_at",
                "type": "timestamp",
                "description": "Creation timestamp",
                "ai_tags": ["time_series"]
            },
        ],
        tags=["servicenow", "configuration_item", "staging"],
        owner="data-platform",
        row_count=None,
        pipeline_status=PipelineStatusEnum.UNKNOWN,
        dbt_model_name="stg_servicenow_configuration_items",
        airflow_dag_id=None
    )

    # Asset 3: incidents_with_configuration_items
    asset3 = CatalogAsset(
        name="incidents_with_configuration_items",
        display_name="Incidents with Configuration Items (Mart)",
        description="Incidents enriched with latest configuration item name",
        schema_name="analytics",
        table_name="incidents_with_configuration_items",
        database="airflow",
        source_system=SourceSystemEnum.DBT,
        columns=[
            {
                "name": "incident_id",
                "type": "uuid",
                "description": "Primary key",
                "ai_tags": ["join_key", "dedup"]
            },
            {
                "name": "configuration_item_name",
                "type": "text",
                "description": "Configuration item name",
                "ai_tags": ["NLP", "embedding", "routing"]
            },
        ],
        tags=["dbt", "incident", "mart", "enriched"],
        owner="data-platform",
        row_count=None,
        pipeline_status=PipelineStatusEnum.UNKNOWN,
        dbt_model_name="incidents_with_configuration_items",
        airflow_dag_id=None
    )

    # Asset 4: stg_servicenow_change_requests
    asset4 = CatalogAsset(
        name="stg_servicenow_change_requests",
        display_name="ServiceNow Change Requests (Staging)",
        description="Cleaned change requests sourced from Supabase",
        schema_name="staging",
        table_name="stg_servicenow_change_requests",
        database="airflow",
        source_system=SourceSystemEnum.SUPABASE,
        columns=[
            {
                "name": "change_request_id",
                "type": "uuid",
                "description": "Primary key",
                "ai_tags": ["join_key", "dedup"]
            },
            {
                "name": "change_request_number",
                "type": "text",
                "description": "Change request number",
                "ai_tags": ["display_key"]
            },
            {
                "name": "status",
                "type": "text",
                "description": "Change status",
                "ai_tags": ["label", "workflow"]
            },
            {
                "name": "created_at",
                "type": "timestamp",
                "description": "Creation timestamp",
                "ai_tags": ["time_series"]
            },
        ],
        tags=["servicenow", "change", "staging"],
        owner="data-platform",
        row_count=None,
        pipeline_status=PipelineStatusEnum.UNKNOWN,
        dbt_model_name="stg_servicenow_change_requests",
        airflow_dag_id=None
    )

    # Asset 5: incidents_with_change_requests
    asset5 = CatalogAsset(
        name="incidents_with_change_requests",
        display_name="Incidents with Change Requests (Mart)",
        description="Incidents linked with their associated change requests",
        schema_name="analytics",
        table_name="incidents_with_change_requests",
        database="airflow",
        source_system=SourceSystemEnum.DBT,
        columns=[
            {
                "name": "incident_id",
                "type": "uuid",
                "description": "Primary key",
                "ai_tags": ["join_key", "dedup"]
            },
            {
                "name": "change_request_number",
                "type": "text",
                "description": "Associated change request number",
                "ai_tags": ["join_key"]
            },
        ],
        tags=["dbt", "incident", "change", "mart", "enriched"],
        owner="data-platform",
        row_count=None,
        pipeline_status=PipelineStatusEnum.UNKNOWN,
        dbt_model_name="incidents_with_change_requests",
        airflow_dag_id=None
    )

    # Add all assets to session
    session.add_all([asset1, asset2, asset3, asset4, asset5])
    await session.commit()

    logger.info("Seeded 5 catalog assets: stg_servicenow_incidents, stg_servicenow_configuration_items, incidents_with_configuration_items, stg_servicenow_change_requests, incidents_with_change_requests")
