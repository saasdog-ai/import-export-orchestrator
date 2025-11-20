"""Interface for cloud storage operations."""

from abc import ABC, abstractmethod


class CloudStorageInterface(ABC):
    """Interface for cloud storage operations (S3, Azure Blob, GCP Cloud Storage)."""

    @abstractmethod
    async def upload_file(
        self, local_file_path: str, remote_file_path: str, content_type: str | None = None
    ) -> str:
        """
        Upload a local file to cloud storage.

        Args:
            local_file_path: Path to the local file
            remote_file_path: Path/name for the file in cloud storage
            content_type: MIME type of the file (e.g., 'text/csv', 'application/json')

        Returns:
            The object key/path in cloud storage
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_presigned_url(
        self, remote_file_path: str, expiration_seconds: int = 3600
    ) -> str:
        """
        Generate a pre-signed URL for downloading a file.

        Args:
            remote_file_path: Path/name of the file in cloud storage
            expiration_seconds: URL expiration time in seconds (default: 1 hour)

        Returns:
            Pre-signed URL for downloading the file
        """
        raise NotImplementedError

    @abstractmethod
    async def download_file(self, remote_file_path: str, local_file_path: str) -> str:
        """
        Download a file from cloud storage to local path.

        Args:
            remote_file_path: Path/name of the file in cloud storage
            local_file_path: Local path where file should be saved

        Returns:
            Path to the downloaded local file
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_file(self, remote_file_path: str) -> None:
        """
        Delete a file from cloud storage.

        Args:
            remote_file_path: Path/name of the file in cloud storage
        """
        raise NotImplementedError
