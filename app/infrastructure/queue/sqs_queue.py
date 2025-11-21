"""AWS SQS queue implementation."""

import asyncio
import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    logger.warning("boto3 not installed. SQS queue will not be available.")


class SQSQueue:
    """AWS SQS queue implementation."""

    def __init__(self, queue_name: str, region: str = "us-east-1"):
        """Initialize SQS queue."""
        if boto3 is None:
            raise ImportError("boto3 is required for SQS. Install with: pip install boto3")

        self.queue_name = queue_name
        self.region = region

        # Use default credential chain (IAM role, env vars, etc.)
        self.sqs_client = boto3.client("sqs", region_name=region)

        # Get queue URL (lazy initialization - will be set on first use if needed)
        self.queue_url = None
        self._queue_name = queue_name

    async def _ensure_queue_url(self) -> None:
        """Ensure queue URL is set, creating queue if necessary."""
        if self.queue_url:
            return

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None, lambda: self.sqs_client.get_queue_url(QueueName=self._queue_name)
            )
            self.queue_url = response["QueueUrl"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "AWS.SimpleQueueService.NonExistentQueue":
                logger.warning(f"Queue '{self._queue_name}' does not exist. Creating it...")
                # Try to create it
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.sqs_client.create_queue(
                            QueueName=self._queue_name,
                            Attributes={
                                "VisibilityTimeout": "300",  # 5 minutes
                                "MessageRetentionPeriod": "1209600",  # 14 days
                            },
                        ),
                    )
                    self.queue_url = response["QueueUrl"]
                    logger.info(f"Created SQS queue: {self._queue_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create queue: {create_error}")
                    raise
            else:
                raise

    async def send_message(self, message_body: dict[str, Any], delay_seconds: int = 0) -> str:
        """Send a message to SQS queue."""
        # Log external service call input
        logger.info(
            f"Message queue send_message request: service=SQS, queue={self.queue_name}, "
            f"message_keys={list(message_body.keys())}, delay_seconds={delay_seconds}"
        )

        await self._ensure_queue_url()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs_client.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(message_body),
                    DelaySeconds=delay_seconds,
                ),
            )
            message_id = response["MessageId"]

            # Log external service call output
            logger.info(
                f"Message queue send_message completed: service=SQS, queue={self.queue_name}, "
                f"message_id={message_id}"
            )
            return message_id
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}")
            raise

    async def receive_messages(
        self, max_messages: int = 1, wait_time_seconds: int = 20
    ) -> list[dict[str, Any]]:
        """Receive messages from SQS queue."""
        # Log external service call input
        logger.debug(
            f"Message queue receive_messages request: service=SQS, queue={self.queue_name}, "
            f"max_messages={max_messages}, wait_time_seconds={wait_time_seconds}"
        )

        await self._ensure_queue_url()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs_client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=min(max_messages, 10),  # SQS max is 10
                    WaitTimeSeconds=wait_time_seconds,
                    AttributeNames=["All"],
                ),
            )

            messages = []
            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg["Body"])
                    messages.append(
                        {
                            "body": body,
                            "receipt_handle": msg["ReceiptHandle"],
                            "message_id": msg["MessageId"],
                        }
                    )
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message body: {msg.get('Body')}")
                    continue

            # Log external service call output
            logger.info(
                f"Message queue receive_messages completed: service=SQS, queue={self.queue_name}, "
                f"message_count={len(messages)}"
            )
            return messages
        except ClientError as e:
            logger.error(f"Failed to receive messages from SQS: {e}")
            raise

    async def delete_message(self, receipt_handle: str) -> None:
        """Delete a message from SQS."""
        # Log external service call input
        logger.debug(
            f"Message queue delete_message request: service=SQS, queue={self.queue_name}, "
            f"receipt_handle_length={len(receipt_handle)}"
        )

        await self._ensure_queue_url()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.sqs_client.delete_message(
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
                ),
            )

            # Log external service call output
            logger.debug(
                f"Message queue delete_message completed: service=SQS, queue={self.queue_name}"
            )
        except ClientError as e:
            logger.error(f"Failed to delete message from SQS: {e}")
            raise

    async def get_queue_attributes(self) -> dict[str, Any]:
        """Get SQS queue attributes."""
        await self._ensure_queue_url()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs_client.get_queue_attributes(
                    QueueUrl=self.queue_url, AttributeNames=["All"]
                ),
            )
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error(f"Failed to get queue attributes: {e}")
            raise
