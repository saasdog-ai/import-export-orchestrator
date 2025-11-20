"""Message queue infrastructure for job processing."""

from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.queue.factory import get_message_queue

__all__ = ["MessageQueueInterface", "get_message_queue"]

