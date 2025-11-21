"""AWS S3 storage implementation."""

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    logger.warning("boto3 not installed. S3 storage will not be available.")


class S3Storage:
    """AWS S3 storage implementation."""

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """Initialize S3 storage."""
        if boto3 is None:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")

        self.bucket_name = bucket_name
        self.region = region

        # Use default credential chain (IAM role, env vars, etc.)
        self.s3_client = boto3.client(
            "s3",
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    async def upload_file(
        self, local_file_path: str, remote_file_path: str, content_type: str | None = None
    ) -> str:
        """Upload a file to S3."""
        # Log external service call input
        import os

        file_size = (
            os.path.getsize(local_file_path) if os.path.exists(local_file_path) else "unknown"
        )
        logger.info(
            f"Cloud storage upload request: service=S3, bucket={self.bucket_name}, "
            f"remote_path={remote_file_path}, local_path={local_file_path}, "
            f"file_size={file_size} bytes, content_type={content_type}"
        )

        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Run synchronous boto3 operation in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_file(
                    local_file_path, self.bucket_name, remote_file_path, ExtraArgs=extra_args
                ),
            )

            # Log external service call output
            logger.info(
                f"Cloud storage upload completed: service=S3, bucket={self.bucket_name}, "
                f"remote_path={remote_file_path}, file_size={file_size} bytes"
            )
            return remote_file_path
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    async def generate_presigned_url(
        self, remote_file_path: str, expiration_seconds: int = 3600
    ) -> str:
        """Generate a pre-signed URL for downloading from S3."""
        # Log external service call input
        logger.info(
            f"Cloud storage presigned URL request: service=S3, bucket={self.bucket_name}, "
            f"remote_path={remote_file_path}, expiration_seconds={expiration_seconds}"
        )

        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": remote_file_path},
                    ExpiresIn=expiration_seconds,
                ),
            )

            # Log external service call output (don't log full URL as it contains sensitive tokens)
            logger.info(
                f"Cloud storage presigned URL generated: service=S3, bucket={self.bucket_name}, "
                f"remote_path={remote_file_path}, url_length={len(url)}"
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            raise

    async def download_file(self, remote_file_path: str, local_file_path: str) -> str:
        """Download a file from S3 to local path."""
        # Log external service call input
        logger.info(
            f"Cloud storage download request: service=S3, bucket={self.bucket_name}, "
            f"remote_path={remote_file_path}, local_path={local_file_path}"
        )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.download_file(
                    self.bucket_name, remote_file_path, local_file_path
                ),
            )

            # Log external service call output
            import os

            file_size = (
                os.path.getsize(local_file_path) if os.path.exists(local_file_path) else "unknown"
            )
            logger.info(
                f"Cloud storage download completed: service=S3, bucket={self.bucket_name}, "
                f"remote_path={remote_file_path}, local_path={local_file_path}, "
                f"file_size={file_size} bytes"
            )
            return local_file_path
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise

    async def delete_file(self, remote_file_path: str) -> None:
        """Delete a file from S3."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_file_path),
            )
            logger.info(f"Deleted s3://{self.bucket_name}/{remote_file_path}")
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise
