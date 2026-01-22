"""Application configuration using Pydantic Settings."""

from functools import lru_cache

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

    # JWT Authentication
    auth_enabled: bool = Field(
        default=False,
        description="Enable JWT authentication. Must be True in production.",
    )
    jwt_jwks_url: str | None = Field(
        default=None,
        description="JWKS endpoint URL for fetching public keys (e.g., https://your-auth.com/.well-known/jwks.json)",
    )
    jwt_issuer: str | None = Field(
        default=None,
        description="Expected JWT issuer (iss claim). If set, tokens must have matching issuer.",
    )
    jwt_audience: str | None = Field(
        default=None,
        description="Expected JWT audience (aud claim). If set, tokens must have matching audience.",
    )
    jwt_client_id_claim: str = Field(
        default="client_id",
        description="JWT claim name containing the client ID. Falls back to 'sub' if not found.",
    )
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT signing algorithm. Use RS256 for asymmetric (JWKS), HS256 for symmetric.",
    )
    jwt_secret_key: str = Field(
        default="CHANGE_THIS_IN_PRODUCTION",
        description="Secret key for HS256 algorithm. Not used when JWKS is configured.",
    )
    jwt_jwks_cache_ttl: int = Field(
        default=3600,
        description="JWKS cache TTL in seconds (default: 1 hour)",
    )
    jwt_access_token_expire_minutes: int = Field(default=30)
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for API protection.",
    )

    # Scheduler
    scheduler_enabled: bool = Field(default=True)
    scheduler_timezone: str = Field(default="UTC")

    # Job Runner
    job_runner_max_workers: int = Field(default=5)
    job_runner_queue_size: int = Field(default=100)

    # AWS (optional - use IAM roles in production)
    aws_region: str | None = Field(default=None)
    aws_access_key_id: str | None = Field(default=None)
    aws_secret_access_key: str | None = Field(default=None)

    # RDS (optional - use AWS Secrets Manager in production)
    rds_host: str | None = Field(default=None)
    rds_port: int = Field(default=5432)
    rds_db_name: str | None = Field(default=None)
    rds_username: str | None = Field(default=None)
    rds_password: str | None = Field(default=None)

    # Cloud Storage (AWS S3, Azure Blob, GCP Cloud Storage)
    cloud_provider: str | None = Field(
        default=None, description="Cloud provider: 'aws', 'azure', or 'gcp'"
    )
    cloud_storage_bucket: str | None = Field(
        default=None, description="Bucket/container name for cloud storage"
    )
    azure_storage_account_name: str | None = Field(default=None)
    export_file_format: str = Field(
        default="csv", description="Default export format: 'csv' or 'json'"
    )
    export_local_path: str = Field(
        default="/tmp/exports", description="Local directory for temporary export files"
    )
    presigned_url_expiration: int = Field(
        default=3600, description="Pre-signed URL expiration in seconds (default: 1 hour)"
    )

    # Message Queue (SQS, Azure Queue, GCP Pub/Sub)
    message_queue_name: str | None = Field(
        default=None, description="Queue name/topic name for message queue"
    )
    message_queue_wait_time: int = Field(
        default=20, description="Long polling wait time in seconds for queue (default: 20)"
    )
    message_queue_max_messages: int = Field(
        default=1, description="Max messages to receive per poll (default: 1)"
    )

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins. Must be explicitly configured in production.",
    )

    # Database pool configuration
    database_pool_recycle: int = Field(
        default=3600, description="Connection pool recycle time in seconds (default: 1 hour)"
    )
    database_pool_timeout: int = Field(
        default=30, description="Connection pool timeout in seconds (default: 30)"
    )

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")

    def model_post_init(self, __context: object) -> None:
        """Validate configuration after initialization."""
        if self.app_env == "production":
            self._validate_production_settings()

    def _validate_production_settings(self) -> None:
        """Validate required settings for production environment."""
        errors: list[str] = []

        if not self.auth_enabled:
            errors.append("Authentication must be enabled in production (set AUTH_ENABLED=true)")

        # JWT configuration validation
        if self.auth_enabled:
            if self.jwt_algorithm.startswith("RS") or self.jwt_algorithm.startswith("ES"):
                # Asymmetric algorithms require JWKS URL
                if not self.jwt_jwks_url:
                    errors.append(
                        f"JWKS URL is required for {self.jwt_algorithm} algorithm (set JWT_JWKS_URL)"
                    )
            else:
                # Symmetric algorithms require secret key
                if self.jwt_secret_key == "CHANGE_THIS_IN_PRODUCTION":
                    errors.append(
                        "JWT secret key must be changed in production (set JWT_SECRET_KEY to a secure value)"
                    )

        if not self.message_queue_name:
            errors.append("Message queue must be configured in production (set MESSAGE_QUEUE_NAME)")

        if self.cloud_provider and not self.cloud_storage_bucket:
            errors.append(
                "Cloud storage bucket must be configured when cloud provider is set "
                "(set CLOUD_STORAGE_BUCKET)"
            )

        if not self.allowed_origins or "*" in self.allowed_origins:
            errors.append(
                "CORS origins must be explicitly configured in production "
                "(set ALLOWED_ORIGINS to specific domains, not '*')"
            )

        if errors:
            error_message = "Production configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise ValueError(error_message)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
