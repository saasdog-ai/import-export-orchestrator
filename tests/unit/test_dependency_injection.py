"""Unit tests for dependency injection."""

from unittest.mock import patch

import pytest

from app.core.dependency_injection import (
    get_cloud_storage,
    get_database,
    get_job_repository,
    get_job_run_repository,
    get_job_runner,
    get_job_service,
    get_message_queue,
    get_query_engine,
    get_scheduler_service,
)


def test_get_database_not_initialized():
    """Test getting DB when not initialized."""
    with patch("app.core.dependency_injection._db", None):
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_database()


def test_get_job_repository_not_initialized():
    """Test getting job repository when not initialized."""
    with patch("app.core.dependency_injection._job_repository", None):
        with pytest.raises(RuntimeError, match="Job repository not initialized"):
            get_job_repository()


def test_get_job_run_repository_not_initialized():
    """Test getting job run repository when not initialized."""
    with patch("app.core.dependency_injection._job_run_repository", None):
        with pytest.raises(RuntimeError, match="Job run repository not initialized"):
            get_job_run_repository()


def test_get_query_engine_not_initialized():
    """Test getting query engine when not initialized."""
    with patch("app.core.dependency_injection._query_engine", None):
        with pytest.raises(RuntimeError, match="Query engine not initialized"):
            get_query_engine()


def test_get_job_service_not_initialized():
    """Test getting job service when not initialized."""
    with patch("app.core.dependency_injection._job_service", None):
        with pytest.raises(RuntimeError, match="Job service not initialized"):
            get_job_service()


def test_get_job_runner_not_initialized():
    """Test getting job runner when not initialized."""
    with patch("app.core.dependency_injection._job_runner", None):
        with pytest.raises(RuntimeError, match="Job runner not initialized"):
            get_job_runner()


def test_get_scheduler_service_not_initialized():
    """Test getting scheduler service when not initialized."""
    with patch("app.core.dependency_injection._scheduler_service", None):
        with pytest.raises(RuntimeError, match="Scheduler service not initialized"):
            get_scheduler_service()


def test_get_cloud_storage_optional():
    """Test getting cloud storage (can be None)."""
    with patch("app.core.dependency_injection._cloud_storage", None):
        result = get_cloud_storage()
        assert result is None


def test_get_message_queue_optional():
    """Test getting message queue (can be None)."""
    with patch("app.core.dependency_injection._message_queue", None):
        result = get_message_queue()
        assert result is None
