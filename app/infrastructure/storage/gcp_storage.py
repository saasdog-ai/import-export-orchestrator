"""Google Cloud Storage implementation."""

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from google.cloud import storage
    from google.cloud.exceptions import GoogleCloudError
except ImportError:
    storage = None
    logger.warning("google-cloud-storage not installed. GCP storage will not be available.")


class GCPCloudStorage:
    """Google Cloud Storage implementation."""

    def __init__(self, bucket_name: str):
        """Initialize GCP Cloud Storage."""
        if storage is None:
            raise ImportError(
                "google-cloud-storage is required for GCP storage. Install with: pip install google-cloud-storage"
            )

        self.bucket_name = bucket_name

        # Use default credential chain (Service Account, Application Default Credentials, etc.)
        self.storage_client = storage.Client()

    async def upload_file(
        self, local_file_path: str, remote_file_path: str, content_type: str | None = None
    ) -> str:
        """Upload a file to GCP Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(remote_file_path)

            if content_type:
                blob.content_type = content_type

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: blob.upload_from_filename(local_file_path))

            logger.info(
                f"Uploaded {local_file_path} to GCP bucket {self.bucket_name}/{remote_file_path}"
            )
            return remote_file_path
        except GoogleCloudError as e:
            logger.error(f"Failed to upload file to GCP: {e}")
            raise

    async def generate_presigned_url(
        self, remote_file_path: str, expiration_seconds: int = 3600
    ) -> str:
        """Generate a signed URL for downloading from GCP Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(remote_file_path)

            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: blob.generate_signed_url(expiration=expiration_seconds, method="GET"),
            )
            return url
        except GoogleCloudError as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise

    async def download_file(self, remote_file_path: str, local_file_path: str) -> str:
        """Download a file from GCP Cloud Storage to local path."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(remote_file_path)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: blob.download_to_filename(local_file_path))

            logger.info(
                f"Downloaded GCP blob {self.bucket_name}/{remote_file_path} to {local_file_path}"
            )
            return local_file_path
        except GoogleCloudError as e:
            logger.error(f"Failed to download file from GCP: {e}")
            raise

    async def delete_file(self, remote_file_path: str) -> None:
        """Delete a file from GCP Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(remote_file_path)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: blob.delete())

            logger.info(f"Deleted GCP blob {self.bucket_name}/{remote_file_path}")
        except GoogleCloudError as e:
            logger.error(f"Failed to delete file from GCP: {e}")
            raise
