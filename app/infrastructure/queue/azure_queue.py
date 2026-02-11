"""Azure Queue Storage implementation."""

import asyncio
import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from azure.core.exceptions import AzureError
    from azure.storage.queue import QueueServiceClient
except ImportError:
    QueueServiceClient = None
    logger.warning("azure-storage-queue not installed. Azure queue will not be available.")


class AzureQueueStorage:
    """Azure Queue Storage implementation."""

    def __init__(self, queue_name: str, account_name: str):
        """Initialize Azure Queue Storage."""
        if QueueServiceClient is None:
            raise ImportError(
                "azure-storage-queue is required for Azure queue. Install with: pip install azure-storage-queue"
            )

        self.queue_name = queue_name
        self.account_name = account_name

        # Use default credential chain (Managed Identity, env vars, etc.)
        import os

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            # Use connection string if available (for local dev)
            self.queue_service_client = QueueServiceClient.from_connection_string(connection_string)
        else:
            # Use DefaultAzureCredential for Managed Identity (production)
            from azure.identity import DefaultAzureCredential

            account_url = f"https://{account_name}.queue.core.windows.net"
            credential = DefaultAzureCredential()
            self.queue_service_client = QueueServiceClient(
                account_url=account_url, credential=credential
            )

        # Queue client will be initialized lazily
        self._queue_name = queue_name
        self.queue_client: Any = None

    async def _ensure_queue_client(self) -> None:
        """Ensure queue client is initialized, creating queue if necessary."""
        if self.queue_client:
            return

        loop = asyncio.get_event_loop()
        try:
            self.queue_client = await loop.run_in_executor(
                None, lambda: self.queue_service_client.get_queue_client(self._queue_name)
            )
            # Try to get properties to check if queue exists
            await loop.run_in_executor(None, lambda: self.queue_client.get_queue_properties())
        except AzureError:
            # Queue doesn't exist, create it
            try:
                self.queue_client = await loop.run_in_executor(
                    None, lambda: self.queue_service_client.create_queue(self._queue_name)
                )
                logger.info(f"Created Azure queue: {self._queue_name}")
            except AzureError as e:
                logger.error(f"Failed to create queue: {e}")
                raise

    async def send_message(self, message_body: dict[str, Any], delay_seconds: int = 0) -> str:
        """Send a message to Azure Queue."""
        # Log external service call input
        logger.info(
            f"Message queue send_message request: service=Azure, queue={self.queue_name}, "
            f"message_keys={list(message_body.keys())}, delay_seconds={delay_seconds}"
        )

        await self._ensure_queue_client()
        try:
            message_text = json.dumps(message_body)
            visibility_timeout = delay_seconds if delay_seconds > 0 else None

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.queue_client.send_message(
                    message_text, visibility_timeout=visibility_timeout
                ),
            )
            message_id = response.id

            # Log external service call output
            logger.info(
                f"Message queue send_message completed: service=Azure, queue={self.queue_name}, "
                f"message_id={message_id}"
            )
            return str(message_id)
        except AzureError as e:
            logger.error(f"Failed to send message to Azure queue: {e}")
            raise

    async def receive_messages(
        self, max_messages: int = 1, wait_time_seconds: int = 20
    ) -> list[dict[str, Any]]:
        """Receive messages from Azure Queue."""
        # Log external service call input
        logger.debug(
            f"Message queue receive_messages request: service=Azure, queue={self.queue_name}, "
            f"max_messages={max_messages}, wait_time_seconds={wait_time_seconds}"
        )

        await self._ensure_queue_client()
        try:
            # Azure Queue Storage doesn't support long polling like SQS
            # We'll use a short timeout and implement polling in the worker
            loop = asyncio.get_event_loop()
            messages = await loop.run_in_executor(
                None,
                lambda: self.queue_client.receive_messages(
                    messages_per_page=min(max_messages, 32),  # Azure max is 32
                    visibility_timeout=60,  # 60 seconds - short to enable fast retry
                ),
            )

            result = []
            for msg in messages:
                try:
                    body = json.loads(msg.content)
                    result.append(
                        {
                            "body": body,
                            "receipt_handle": f"{msg.id}:{msg.pop_receipt}",  # Store both for deletion
                            "message_id": msg.id,
                            "pop_receipt": msg.pop_receipt,  # Store separately for deletion
                        }
                    )
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message content: {msg.content}")
                    continue

            # Log external service call output
            logger.info(
                f"Message queue receive_messages completed: service=Azure, queue={self.queue_name}, "
                f"message_count={len(result)}"
            )
            return result
        except AzureError as e:
            logger.error(f"Failed to receive messages from Azure queue: {e}")
            raise

    async def delete_message(self, receipt_handle: str) -> None:
        """Delete a message from Azure Queue."""
        # Log external service call input
        logger.debug(
            f"Message queue delete_message request: service=Azure, queue={self.queue_name}, "
            f"receipt_handle_length={len(receipt_handle)}"
        )

        await self._ensure_queue_client()
        try:
            # Parse receipt_handle which contains "message_id:pop_receipt"
            if ":" in receipt_handle:
                message_id, pop_receipt = receipt_handle.split(":", 1)
            else:
                # Fallback: try to extract from message dict if available
                # This won't work in practice, but provides a fallback
                logger.warning(
                    f"Azure queue delete_message: receipt_handle format unexpected: {receipt_handle}"
                )
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.queue_client.delete_message(message_id, pop_receipt)
            )

            # Log external service call output
            logger.debug(
                f"Message queue delete_message completed: service=Azure, queue={self.queue_name}"
            )
        except AzureError as e:
            logger.error(f"Failed to delete message from Azure queue: {e}")
            raise

    async def get_queue_attributes(self) -> dict[str, Any]:
        """Get Azure Queue attributes."""
        await self._ensure_queue_client()
        try:
            loop = asyncio.get_event_loop()
            properties = await loop.run_in_executor(
                None, lambda: self.queue_client.get_queue_properties()
            )
            return {
                "approximate_messages_count": properties.approximate_message_count,
            }
        except AzureError as e:
            logger.error(f"Failed to get queue attributes: {e}")
            raise

    async def extend_message_visibility(
        self, receipt_handle: str, visibility_timeout_seconds: int
    ) -> None:
        """Extend message visibility timeout for long-running jobs."""
        logger.debug(
            f"Message queue extend_visibility request: service=Azure, queue={self.queue_name}, "
            f"timeout={visibility_timeout_seconds}s"
        )

        await self._ensure_queue_client()
        try:
            # Parse receipt_handle which contains "message_id:pop_receipt"
            if ":" not in receipt_handle:
                logger.warning(
                    f"Azure queue extend_visibility: receipt_handle format unexpected: {receipt_handle}"
                )
                return

            message_id, pop_receipt = receipt_handle.split(":", 1)

            loop = asyncio.get_event_loop()
            # Azure uses update_message with empty content to extend visibility
            await loop.run_in_executor(
                None,
                lambda: self.queue_client.update_message(
                    message_id,
                    pop_receipt,
                    visibility_timeout=visibility_timeout_seconds,
                ),
            )

            logger.debug(
                f"Message queue extend_visibility completed: service=Azure, queue={self.queue_name}"
            )
        except AzureError as e:
            logger.error(f"Failed to extend message visibility: {e}")
            raise
