"""Cloud storage infrastructure for file uploads."""

from app.infrastructure.storage.interface import CloudStorageInterface
from app.infrastructure.storage.factory import get_cloud_storage

__all__ = ["CloudStorageInterface", "get_cloud_storage"]

