"""Azure Blob Storage implementation."""

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from azure.core.exceptions import AzureError
    from azure.storage.blob import BlobServiceClient
except ImportError:
    BlobServiceClient = None
    logger.warning("azure-storage-blob not installed. Azure storage will not be available.")


class AzureBlobStorage:
    """Azure Blob Storage implementation."""

    def __init__(self, container_name: str, account_name: str | None = None):
        """Initialize Azure Blob Storage."""
        if BlobServiceClient is None:
            raise ImportError(
                "azure-storage-blob is required for Azure storage. Install with: pip install azure-storage-blob"
            )

        self.container_name = container_name
        self.account_name = account_name

        # Use default credential chain (Managed Identity, env vars, etc.)
        # For local dev, can use connection string or account key
        # In production, use Managed Identity
        import os

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            # Use connection string if available (for local dev)
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Use DefaultAzureCredential for Managed Identity (production)
            from azure.identity import DefaultAzureCredential

            if not account_name:
                raise ValueError(
                    "azure_storage_account_name is required when not using connection string"
                )
            account_url = f"https://{account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=credential
            )

    async def upload_file(
        self, local_file_path: str, remote_file_path: str, content_type: str | None = None
    ) -> str:
        """Upload a file to Azure Blob Storage."""
        # Log external service call input
        import os

        file_size = (
            os.path.getsize(local_file_path) if os.path.exists(local_file_path) else "unknown"
        )
        logger.info(
            f"Cloud storage upload request: service=Azure, container={self.container_name}, "
            f"remote_path={remote_file_path}, local_path={local_file_path}, "
            f"file_size={file_size} bytes, content_type={content_type}"
        )

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            content_settings = {}
            if content_type:
                content_settings["content_type"] = content_type

            loop = asyncio.get_event_loop()
            with open(local_file_path, "rb") as data:
                await loop.run_in_executor(
                    None,
                    lambda: blob_client.upload_blob(
                        data, overwrite=True, content_settings=content_settings
                    ),
                )

            # Log external service call output
            logger.info(
                f"Cloud storage upload completed: service=Azure, container={self.container_name}, "
                f"remote_path={remote_file_path}, file_size={file_size} bytes"
            )
            return remote_file_path
        except AzureError as e:
            logger.error(f"Failed to upload file to Azure: {e}")
            raise

    async def download_file(self, remote_file_path: str, local_file_path: str) -> str:
        """Download a file from Azure Blob Storage to local path."""
        # Log external service call input
        logger.info(
            f"Cloud storage download request: service=Azure, container={self.container_name}, "
            f"remote_path={remote_file_path}, local_path={local_file_path}"
        )

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            loop = asyncio.get_event_loop()
            with open(local_file_path, "wb") as download_file:
                await loop.run_in_executor(
                    None, lambda: blob_client.download_blob().readinto(download_file)
                )

            # Log external service call output
            import os

            file_size = (
                os.path.getsize(local_file_path) if os.path.exists(local_file_path) else "unknown"
            )
            logger.info(
                f"Cloud storage download completed: service=Azure, container={self.container_name}, "
                f"remote_path={remote_file_path}, local_path={local_file_path}, "
                f"file_size={file_size} bytes"
            )
            return local_file_path
        except AzureError as e:
            logger.error(f"Failed to download file from Azure: {e}")
            raise

    async def generate_presigned_url(
        self, remote_file_path: str, expiration_seconds: int = 3600
    ) -> str:
        """Generate a SAS (Shared Access Signature) URL for downloading."""
        # Log external service call input
        logger.info(
            f"Cloud storage presigned URL request: service=Azure, container={self.container_name}, "
            f"remote_path={remote_file_path}, expiration_seconds={expiration_seconds}"
        )

        try:
            from datetime import UTC, datetime, timedelta

            from azure.storage.blob import BlobSasPermissions, generate_blob_sas

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            # Generate SAS token using the blob client's account key or credential
            # Note: For production with Managed Identity, you may need to use
            # User Delegation SAS instead of account key SAS
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=remote_file_path,
                account_key=None,  # Will use credential if available
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(UTC) + timedelta(seconds=expiration_seconds),
            )

            url = f"{blob_client.url}?{sas_token}"

            # Log external service call output (don't log full URL as it contains sensitive tokens)
            logger.info(
                f"Cloud storage presigned URL generated: service=Azure, container={self.container_name}, "
                f"remote_path={remote_file_path}, url_length={len(url)}"
            )
            return url
        except AzureError as e:
            logger.error(f"Failed to generate SAS URL: {e}")
            raise

    async def generate_presigned_upload_url(
        self, remote_file_path: str, content_type: str, expiration_seconds: int = 3600
    ) -> str:
        """Generate a SAS URL for uploading to Azure Blob Storage."""
        logger.info(
            f"Cloud storage presigned upload URL request: service=Azure, "
            f"container={self.container_name}, remote_path={remote_file_path}, "
            f"content_type={content_type}, expiration_seconds={expiration_seconds}"
        )

        try:
            from datetime import UTC, datetime, timedelta

            from azure.storage.blob import BlobSasPermissions, generate_blob_sas

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=remote_file_path,
                account_key=None,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.now(UTC) + timedelta(seconds=expiration_seconds),
            )

            url = f"{blob_client.url}?{sas_token}"

            logger.info(
                f"Cloud storage presigned upload URL generated: service=Azure, "
                f"container={self.container_name}, remote_path={remote_file_path}, "
                f"url_length={len(url)}"
            )
            return url
        except AzureError as e:
            logger.error(f"Failed to generate SAS upload URL: {e}")
            raise

    async def file_exists(self, remote_file_path: str) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: blob_client.get_blob_properties())
            return True
        except Exception:
            # ResourceNotFoundError is raised if blob doesn't exist
            return False

    async def delete_file(self, remote_file_path: str) -> None:
        """Delete a file from Azure Blob Storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=remote_file_path
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: blob_client.delete_blob())

            logger.info(f"Deleted Azure blob {self.container_name}/{remote_file_path}")
        except AzureError as e:
            logger.error(f"Failed to delete file from Azure: {e}")
            raise
