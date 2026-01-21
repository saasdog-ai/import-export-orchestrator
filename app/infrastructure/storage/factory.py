"""Factory for creating cloud storage instances."""

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.storage.interface import CloudStorageInterface

logger = get_logger(__name__)


def get_cloud_storage() -> CloudStorageInterface | None:
    """
    Get cloud storage instance based on configuration.

    Returns:
        CloudStorageInterface instance or None if not configured
    """
    settings = get_settings()
    cloud_provider = settings.cloud_provider

    if cloud_provider is None:
        logger.warning("No cloud provider configured. File exports will not be uploaded.")
        return None

    if cloud_provider == "aws":
        from app.infrastructure.storage.s3_storage import S3Storage

        if not settings.cloud_storage_bucket:
            logger.warning("AWS cloud storage bucket not configured")
            return None
        return S3Storage(  # type: ignore[return-value]
            bucket_name=settings.cloud_storage_bucket,
            region=settings.aws_region or "us-east-1",
        )
    elif cloud_provider == "azure":
        from app.infrastructure.storage.azure_storage import AzureBlobStorage

        if not settings.cloud_storage_bucket or not settings.azure_storage_account_name:
            logger.warning("Azure storage bucket or account name not configured")
            return None
        return AzureBlobStorage(  # type: ignore[return-value]
            container_name=settings.cloud_storage_bucket,
            account_name=settings.azure_storage_account_name,
        )
    elif cloud_provider == "gcp":
        from app.infrastructure.storage.gcp_storage import GCPCloudStorage

        if not settings.cloud_storage_bucket:
            logger.warning("GCP cloud storage bucket not configured")
            return None
        return GCPCloudStorage(  # type: ignore[return-value]
            bucket_name=settings.cloud_storage_bucket,
        )
    else:
        logger.warning(f"Unknown cloud provider: {cloud_provider}")
        return None
