"""Google Cloud Pub/Sub queue implementation."""

import asyncio
import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from google.cloud import pubsub_v1
    from google.cloud.exceptions import GoogleCloudError
except ImportError:
    pubsub_v1 = None
    logger.warning("google-cloud-pubsub not installed. GCP Pub/Sub queue will not be available.")


class GCPPubSubQueue:
    """Google Cloud Pub/Sub queue implementation."""

    def __init__(self, topic_name: str, subscription_name: str):
        """Initialize GCP Pub/Sub queue."""
        if pubsub_v1 is None:
            raise ImportError(
                "google-cloud-pubsub is required for GCP Pub/Sub. Install with: pip install google-cloud-pubsub"
            )

        self.topic_name = topic_name
        self.subscription_name = subscription_name

        # Use default credential chain (Service Account, Application Default Credentials, etc.)
        self.publisher_client = pubsub_v1.PublisherClient()
        self.subscriber_client = pubsub_v1.SubscriberClient()

        # Topic and subscription paths will be initialized lazily
        self.project_id: str | None = None
        self.topic_path: str | None = None
        self.subscription_path: str | None = None

    async def _ensure_topic_and_subscription(self) -> None:
        """Ensure topic and subscription exist, creating them if necessary."""
        if self.topic_path and self.subscription_path:
            return

        # Get project ID from environment or default
        import os

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            # Try to get from Application Default Credentials
            from google.auth import default

            _, project_id = default()

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")

        self.project_id = project_id
        self.topic_path = self.publisher_client.topic_path(project_id, self.topic_name)
        self.subscription_path = self.subscriber_client.subscription_path(
            project_id, self.subscription_name
        )

        # Create topic if it doesn't exist
        try:
            await asyncio.to_thread(self.publisher_client.get_topic, topic=self.topic_path)
        except GoogleCloudError:
            await asyncio.to_thread(self.publisher_client.create_topic, name=self.topic_path)
            logger.info(f"Created Pub/Sub topic: {self.topic_name}")

        # Create subscription if it doesn't exist
        try:
            await asyncio.to_thread(
                self.subscriber_client.get_subscription, subscription=self.subscription_path
            )
        except GoogleCloudError:
            await asyncio.to_thread(
                self.subscriber_client.create_subscription,
                name=self.subscription_path,
                topic=self.topic_path,
            )
            logger.info(f"Created Pub/Sub subscription: {self.subscription_name}")

    async def send_message(self, message_body: dict[str, Any], delay_seconds: int = 0) -> str:
        """Send a message to Pub/Sub."""
        # Log external service call input
        logger.info(
            f"Message queue send_message request: service=GCP, topic={self.topic_name}, "
            f"message_keys={list(message_body.keys())}, delay_seconds={delay_seconds}"
        )

        await self._ensure_topic_and_subscription()
        try:
            message_data = json.dumps(message_body).encode("utf-8")

            # Pub/Sub doesn't support delay_seconds directly, but we can use message attributes
            future = await asyncio.to_thread(
                self.publisher_client.publish,
                self.topic_path,
                message_data,
            )
            message_id = future.result()  # Wait for publish to complete

            # Log external service call output
            logger.info(
                f"Message queue send_message completed: service=GCP, topic={self.topic_name}, "
                f"message_id={message_id}"
            )
            return str(message_id)
        except GoogleCloudError as e:
            logger.error(f"Failed to send message to Pub/Sub: {e}")
            raise

    async def receive_messages(
        self, max_messages: int = 1, wait_time_seconds: int = 20
    ) -> list[dict[str, Any]]:
        """Receive messages from Pub/Sub."""
        # Log external service call input
        logger.debug(
            f"Message queue receive_messages request: service=GCP, subscription={self.subscription_name}, "
            f"max_messages={max_messages}, wait_time_seconds={wait_time_seconds}"
        )

        await self._ensure_topic_and_subscription()
        try:
            # Pub/Sub uses streaming pull, which is more complex
            # For simplicity, we'll use synchronous pull with timeout
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.subscriber_client.pull(
                    subscription=self.subscription_path,
                    max_messages=min(max_messages, 100),  # Pub/Sub max is 100
                    timeout=wait_time_seconds,
                ),
            )

            messages = []
            for msg in response.received_messages:
                try:
                    body = json.loads(msg.message.data.decode("utf-8"))
                    messages.append(
                        {
                            "body": body,
                            "receipt_handle": msg.ack_id,  # Use ack_id as receipt handle
                            "message_id": msg.message.message_id,
                        }
                    )
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue

            # Log external service call output
            logger.info(
                f"Message queue receive_messages completed: service=GCP, subscription={self.subscription_name}, "
                f"message_count={len(messages)}"
            )
            return messages
        except GoogleCloudError as e:
            logger.error(f"Failed to receive messages from Pub/Sub: {e}")
            raise

    async def delete_message(self, receipt_handle: str) -> None:
        """Acknowledge (delete) a message from Pub/Sub."""
        # Log external service call input
        logger.debug(
            f"Message queue delete_message request: service=GCP, subscription={self.subscription_name}, "
            f"receipt_handle_length={len(receipt_handle)}"
        )

        await self._ensure_topic_and_subscription()
        try:
            # Pub/Sub uses ack instead of delete
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.subscriber_client.acknowledge(
                    subscription=self.subscription_path, ack_ids=[receipt_handle]
                ),
            )

            # Log external service call output
            logger.debug(
                f"Message queue delete_message completed: service=GCP, subscription={self.subscription_name}"
            )
        except GoogleCloudError as e:
            logger.error(f"Failed to acknowledge message in Pub/Sub: {e}")
            raise

    async def get_queue_attributes(self) -> dict[str, Any]:
        """Get Pub/Sub subscription attributes."""
        await self._ensure_topic_and_subscription()
        try:
            loop = asyncio.get_event_loop()
            subscription = await loop.run_in_executor(
                None,
                lambda: self.subscriber_client.get_subscription(
                    subscription=self.subscription_path
                ),
            )
            return {
                "num_undelivered_messages": subscription.num_undelivered_messages,
            }
        except GoogleCloudError as e:
            logger.error(f"Failed to get subscription attributes: {e}")
            raise
