"""Factory for creating message queue instances."""

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.queue.interface import MessageQueueInterface

logger = get_logger(__name__)


def get_message_queue() -> MessageQueueInterface | None:
    """
    Get message queue instance based on configuration.

    Returns:
        MessageQueueInterface instance or None if not configured
    """
    settings = get_settings()
    cloud_provider = settings.cloud_provider

    if cloud_provider is None:
        logger.warning(
            "No cloud provider configured. Using in-memory queue (not recommended for production)."
        )
        return None

    queue_name = settings.message_queue_name
    if not queue_name:
        logger.warning(
            "No message queue name configured. Using in-memory queue (not recommended for production)."
        )
        return None

    if cloud_provider == "aws":
        from app.infrastructure.queue.sqs_queue import SQSQueue

        return SQSQueue(  # type: ignore[return-value]
            queue_name=queue_name,
            region=settings.aws_region or "us-east-1",
        )
    elif cloud_provider == "azure":
        from app.infrastructure.queue.azure_queue import AzureQueueStorage

        if not settings.azure_storage_account_name:
            logger.warning("Azure storage account name not configured")
            return None
        return AzureQueueStorage(  # type: ignore[return-value]
            queue_name=queue_name,
            account_name=settings.azure_storage_account_name,
        )
    elif cloud_provider == "gcp":
        from app.infrastructure.queue.gcp_queue import GCPPubSubQueue

        return GCPPubSubQueue(  # type: ignore[return-value]
            topic_name=queue_name,
            subscription_name=f"{queue_name}-subscription",
        )
    else:
        logger.warning(f"Unknown cloud provider: {cloud_provider}")
        return None
