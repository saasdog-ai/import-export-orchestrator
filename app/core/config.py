"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="import-export-orchestrator")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/job_runner"
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=False)

    # Security (for future JWT implementation)
    jwt_secret_key: str = Field(default="CHANGE_THIS_IN_PRODUCTION")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)

    # Scheduler
    scheduler_enabled: bool = Field(default=True)
    scheduler_timezone: str = Field(default="UTC")

    # Job Runner
    job_runner_max_workers: int = Field(default=5)
    job_runner_queue_size: int = Field(default=100)

    # AWS (optional - use IAM roles in production)
    aws_region: Optional[str] = Field(default=None)
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)

    # RDS (optional - use AWS Secrets Manager in production)
    rds_host: Optional[str] = Field(default=None)
    rds_port: int = Field(default=5432)
    rds_db_name: Optional[str] = Field(default=None)
    rds_username: Optional[str] = Field(default=None)
    rds_password: Optional[str] = Field(default=None)

    # Cloud Storage (AWS S3, Azure Blob, GCP Cloud Storage)
    cloud_provider: Optional[str] = Field(
        default=None, description="Cloud provider: 'aws', 'azure', or 'gcp'"
    )
    cloud_storage_bucket: Optional[str] = Field(
        default=None, description="Bucket/container name for cloud storage"
    )
    azure_storage_account_name: Optional[str] = Field(default=None)
    export_file_format: str = Field(default="csv", description="Default export format: 'csv' or 'json'")
    export_local_path: str = Field(
        default="/tmp/exports", description="Local directory for temporary export files"
    )
    presigned_url_expiration: int = Field(
        default=3600, description="Pre-signed URL expiration in seconds (default: 1 hour)"
    )

    # Message Queue (SQS, Azure Queue, GCP Pub/Sub)
    message_queue_name: Optional[str] = Field(
        default=None, description="Queue name/topic name for message queue"
    )
    message_queue_wait_time: int = Field(
        default=20, description="Long polling wait time in seconds for queue (default: 20)"
    )
    message_queue_max_messages: int = Field(
        default=1, description="Max messages to receive per poll (default: 1)"
    )

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

