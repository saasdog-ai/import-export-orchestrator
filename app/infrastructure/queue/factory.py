"""Factory for creating message queue instances."""

import json
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.queue.interface import MessageQueueInterface

logger = get_logger(__name__)


def get_message_queue() -> Optional[MessageQueueInterface]:
    """
    Get message queue instance based on configuration.

    Returns:
        MessageQueueInterface instance or None if not configured
    """
    settings = get_settings()
    cloud_provider = settings.cloud_provider

    if cloud_provider is None:
        logger.warning("No cloud provider configured. Using in-memory queue (not recommended for production).")
        return None

    queue_name = settings.message_queue_name
    if not queue_name:
        logger.warning("No message queue name configured. Using in-memory queue (not recommended for production).")
        return None

    if cloud_provider == "aws":
        from app.infrastructure.queue.sqs_queue import SQSQueue

        return SQSQueue(
            queue_name=queue_name,
            region=settings.aws_region or "us-east-1",
        )
    elif cloud_provider == "azure":
        from app.infrastructure.queue.azure_queue import AzureQueueStorage

        return AzureQueueStorage(
            queue_name=queue_name,
            account_name=settings.azure_storage_account_name,
        )
    elif cloud_provider == "gcp":
        from app.infrastructure.queue.gcp_queue import GCPPubSubQueue

        return GCPPubSubQueue(
            topic_name=queue_name,
            subscription_name=f"{queue_name}-subscription",
        )
    else:
        logger.warning(f"Unknown cloud provider: {cloud_provider}")
        return None

