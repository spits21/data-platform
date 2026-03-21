"""Configuration module using pydantic-settings to read from .env"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    # Anthropic API
    anthropic_api_key: str

    # Local PostgreSQL (airflow database)
    local_pg_host: str = "postgres"
    local_pg_port: int = 5432
    local_pg_db: str = "airflow"
    local_pg_user: str = "airflow"
    local_pg_pass: str = "airflow"

    # Catalog database
    catalog_db_name: str = "catalog_db"

    # Airflow API
    airflow_api_url: str = "http://airflow-webserver:8080/api/v1"
    airflow_admin_user: str = "admin"
    airflow_admin_pass: str = "admin"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def airflow_db_url(self) -> str:
        """PostgreSQL connection URL for airflow database."""
        return (
            f"postgresql+asyncpg://{self.local_pg_user}:{self.local_pg_pass}"
            f"@{self.local_pg_host}:{self.local_pg_port}/{self.local_pg_db}"
        )

    @property
    def catalog_db_url(self) -> str:
        """PostgreSQL connection URL for catalog database."""
        return (
            f"postgresql+asyncpg://{self.local_pg_user}:{self.local_pg_pass}"
            f"@{self.local_pg_host}:{self.local_pg_port}/{self.catalog_db_name}"
        )

    @property
    def asyncpg_airflow_dsn(self) -> str:
        """asyncpg connection string for airflow database (no driver prefix)."""
        return (
            f"postgresql://{self.local_pg_user}:{self.local_pg_pass}"
            f"@{self.local_pg_host}:{self.local_pg_port}/{self.local_pg_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
