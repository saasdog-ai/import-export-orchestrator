"""Interface for message queue operations."""

from abc import ABC, abstractmethod
from typing import Any


class MessageQueueInterface(ABC):
    """Interface for message queue operations (SQS, Azure Queue, GCP Pub/Sub)."""

    @abstractmethod
    async def send_message(self, message_body: dict[str, Any], delay_seconds: int = 0) -> str:
        """
        Send a message to the queue.

        Args:
            message_body: Dictionary containing the message data
            delay_seconds: Delay before message becomes available (default: 0)

        Returns:
            Message ID or receipt handle
        """
        raise NotImplementedError

    @abstractmethod
    async def receive_messages(
        self, max_messages: int = 1, wait_time_seconds: int = 20
    ) -> list[dict[str, Any]]:
        """
        Receive messages from the queue.

        Args:
            max_messages: Maximum number of messages to receive (default: 1)
            wait_time_seconds: Long polling wait time in seconds (default: 20)

        Returns:
            List of messages, each containing 'body' (dict) and 'receipt_handle' (str)
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_message(self, receipt_handle: str) -> None:
        """
        Delete a message from the queue after processing.

        Args:
            receipt_handle: Receipt handle or message ID from receive_messages
        """
        raise NotImplementedError

    @abstractmethod
    async def get_queue_attributes(self) -> dict[str, Any]:
        """
        Get queue attributes (e.g., approximate number of messages).

        Returns:
            Dictionary of queue attributes
        """
        raise NotImplementedError

    @abstractmethod
    async def extend_message_visibility(
        self, receipt_handle: str, visibility_timeout_seconds: int
    ) -> None:
        """
        Extend the visibility timeout of a message.

        Use this for long-running jobs to prevent the message from becoming
        visible again while still being processed.

        Args:
            receipt_handle: Receipt handle from receive_messages
            visibility_timeout_seconds: New visibility timeout in seconds
        """
        raise NotImplementedError
