"""Message queue infrastructure for job processing."""

from app.infrastructure.queue.factory import get_message_queue
from app.infrastructure.queue.interface import MessageQueueInterface

__all__ = ["MessageQueueInterface", "get_message_queue"]
