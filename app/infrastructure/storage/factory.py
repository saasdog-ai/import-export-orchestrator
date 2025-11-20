"""Factory for creating cloud storage instances."""

from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.storage.interface import CloudStorageInterface

logger = get_logger(__name__)


def get_cloud_storage() -> Optional[CloudStorageInterface]:
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

        return S3Storage(
            bucket_name=settings.cloud_storage_bucket,
            region=settings.aws_region or "us-east-1",
        )
    elif cloud_provider == "azure":
        from app.infrastructure.storage.azure_storage import AzureBlobStorage

        return AzureBlobStorage(
            container_name=settings.cloud_storage_bucket,
            account_name=settings.azure_storage_account_name,
        )
    elif cloud_provider == "gcp":
        from app.infrastructure.storage.gcp_storage import GCPCloudStorage

        return GCPCloudStorage(
            bucket_name=settings.cloud_storage_bucket,
        )
    else:
        logger.warning(f"Unknown cloud provider: {cloud_provider}")
        return None

