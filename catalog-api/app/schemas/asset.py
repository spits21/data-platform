"""Pydantic v2 schemas for request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class SourceSystemEnum(str, Enum):
    """Source system classification."""
    SUPABASE = "supabase"
    DBT = "dbt"
    SERVICENOW = "servicenow"


class PipelineStatusEnum(str, Enum):
    """Pipeline health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ColumnInfo(BaseModel):
    """Schema column metadata."""
    name: str
    type: str
    description: Optional[str] = None
    ai_tags: Optional[List[str]] = None


class AssetCreate(BaseModel):
    """Request schema for creating a new asset."""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_name: str = Field(..., min_length=1)
    table_name: str = Field(..., min_length=1)
    source_system: SourceSystemEnum
    columns: Optional[List[ColumnInfo]] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    row_count: Optional[int] = None
    pipeline_status: PipelineStatusEnum = PipelineStatusEnum.UNKNOWN
    dbt_model_name: Optional[str] = None
    airflow_dag_id: Optional[str] = None


class AssetRead(BaseModel):
    """Response schema for asset read operations."""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    schema_name: str
    table_name: str
    database: str
    source_system: SourceSystemEnum
    columns: Optional[List[Dict[str, Any]]]
    tags: List[str]
    owner: Optional[str]
    last_synced_at: Optional[datetime]
    row_count: Optional[int]
    pipeline_status: PipelineStatusEnum
    dbt_model_name: Optional[str]
    airflow_dag_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessage(BaseModel):
    """Single message in conversation history."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Request schema for /ai-lab/chat endpoint."""
    asset_id: int
    message: str = Field(..., min_length=1)
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response schema for /ai-lab/chat endpoint."""
    response: str
    sql_executed: Optional[List[str]] = None
    asset_id: int
    model: str = "claude-haiku-4-5-20251001"
