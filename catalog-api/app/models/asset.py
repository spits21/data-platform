"""SQLAlchemy ORM model for catalog assets."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ARRAY, Enum, func
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class SourceSystemEnum(str, enum.Enum):
    """Source system classification."""
    SUPABASE = "supabase"
    DBT = "dbt"
    SERVICENOW = "servicenow"


class PipelineStatusEnum(str, enum.Enum):
    """Pipeline health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNKNOWN = "unknown"


class CatalogAsset(Base):
    """Catalog asset record in catalog_db."""

    __tablename__ = "catalog_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    schema_name = Column(String, nullable=False)
    table_name = Column(String, nullable=False, index=True)
    database = Column(String, default="airflow", nullable=False)
    source_system = Column(
        Enum(SourceSystemEnum), nullable=False, index=True, default=SourceSystemEnum.SUPABASE
    )
    columns = Column(JSON, nullable=True)  # List of {name, type, description, ai_tags}
    tags = Column(ARRAY(String), nullable=True, default=[])
    owner = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    row_count = Column(Integer, nullable=True)
    pipeline_status = Column(
        Enum(PipelineStatusEnum), nullable=False, default=PipelineStatusEnum.UNKNOWN
    )
    dbt_model_name = Column(String, nullable=True)
    airflow_dag_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CatalogAsset(id={self.id}, name={self.name}, "
            f"schema={self.schema_name}.{self.table_name})>"
        )
