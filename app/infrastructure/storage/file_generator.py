"""File generation utilities for exports."""

import csv
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.constants import (
    CONTENT_TYPE_CSV,
    CONTENT_TYPE_JSON,
    DEFAULT_EXPORT_LOCAL_PATH,
    EXPORT_FORMAT_CSV,
    EXPORT_FORMAT_JSON,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileGenerator:
    """Utility for generating export files."""

    @staticmethod
    def generate_csv_file(
        data: list[dict[str, Any]], fields: list[str], output_dir: str | None = None
    ) -> str:
        """
        Generate a CSV file from data.

        Args:
            data: List of dictionaries containing the data
            fields: List of field names to include in CSV
            output_dir: Directory to save the file (default: from constants)

        Returns:
            Path to the generated CSV file
        """
        if output_dir is None:
            output_dir = DEFAULT_EXPORT_LOCAL_PATH

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = f"export_{uuid4().hex[:8]}.csv"
        file_path = os.path.join(output_dir, filename)

        if not data:
            # Create empty CSV with headers
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
        else:
            # Write data to CSV
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for row in data:
                    # Flatten nested fields (e.g., "vendor.name" -> extract from nested dict)
                    flat_row = {}
                    for field in fields:
                        value = FileGenerator._get_nested_value(row, field)
                        flat_row[field] = value
                    writer.writerow(flat_row)

        logger.info(f"Generated CSV file: {file_path} ({len(data)} records)")
        return file_path

    @staticmethod
    def generate_json_file(data: list[dict[str, Any]], output_dir: str | None = None) -> str:
        """
        Generate a JSON file from data.

        Args:
            data: List of dictionaries containing the data
            output_dir: Directory to save the file (default: from constants)

        Returns:
            Path to the generated JSON file
        """
        if output_dir is None:
            output_dir = DEFAULT_EXPORT_LOCAL_PATH

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = f"export_{uuid4().hex[:8]}.json"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated JSON file: {file_path} ({len(data)} records)")
        return file_path

    @staticmethod
    async def generate_csv_file_streaming(
        batch_generator: AsyncGenerator[list[dict[str, Any]], None],
        fields: list[str],
        output_dir: str | None = None,
    ) -> tuple[str, int]:
        """Write batches to CSV as they arrive.

        Args:
            batch_generator: Async generator yielding lists of record dicts
            fields: Column names for CSV header
            output_dir: Directory to save the file

        Returns:
            Tuple of (file_path, record_count)
        """
        if output_dir is None:
            output_dir = DEFAULT_EXPORT_LOCAL_PATH

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        filename = f"export_{uuid4().hex[:8]}.csv"
        file_path = os.path.join(output_dir, filename)
        record_count = 0

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            async for batch in batch_generator:
                for row in batch:
                    flat_row = {}
                    for field in fields:
                        flat_row[field] = FileGenerator._get_nested_value(row, field)
                    writer.writerow(flat_row)
                    record_count += 1

        logger.info(f"Generated streaming CSV file: {file_path} ({record_count} records)")
        return file_path, record_count

    @staticmethod
    def _get_nested_value(data: dict[str, Any], field_path: str) -> Any:
        """
        Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to extract value from
            field_path: Field path (e.g., "vendor.name" or "amount")

        Returns:
            The value at the field path, or None if not found
        """
        parts = field_path.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value

    @staticmethod
    def get_file_extension(format_type: str) -> str:
        """Get file extension for format type."""
        format_map = {
            EXPORT_FORMAT_CSV: ".csv",
            EXPORT_FORMAT_JSON: ".json",
        }
        return format_map.get(format_type.lower(), ".csv")

    @staticmethod
    def get_content_type(format_type: str) -> str:
        """Get MIME content type for format type."""
        format_map = {
            EXPORT_FORMAT_CSV: CONTENT_TYPE_CSV,
            EXPORT_FORMAT_JSON: CONTENT_TYPE_JSON,
        }
        return format_map.get(format_type.lower(), CONTENT_TYPE_CSV)
