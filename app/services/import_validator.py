"""Validation service for import files."""

import csv
import json
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.domain.entities import ExportEntity

logger = get_logger(__name__)


class ValidationError(Exception):
    """Validation error with row and field information."""

    def __init__(self, message: str, row: int | None = None, field: str | None = None):
        self.message = message
        self.row = row  # 1-based row number (header is row 0)
        self.field = field
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API response."""
        error = {"message": self.message}
        if self.row is not None:
            error["row"] = self.row
        if self.field is not None:
            error["field"] = self.field
        return error


class ImportValidator:
    """Service for validating import files before processing."""

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {".csv", ".json"}

    # Required fields for each entity
    REQUIRED_FIELDS: dict[ExportEntity, list[str]] = {
        ExportEntity.BILL: ["amount", "date"],
        ExportEntity.INVOICE: ["amount", "date"],
        ExportEntity.VENDOR: ["name"],
        ExportEntity.PROJECT: ["code", "name"],
    }

    # Field type validations
    FIELD_TYPES: dict[str, type] = {
        "amount": float,
        "date": str,  # Will validate ISO format
        "id": str,  # UUID format
    }

    @staticmethod
    def validate_file_format(file_path: str) -> tuple[bool, str | None]:
        """
        Validate basic file format (extension, size).

        Returns:
            (is_valid, error_message)
        """
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in ImportValidator.ALLOWED_EXTENSIONS:
            return (
                False,
                f"Invalid file format. Allowed: {', '.join(ImportValidator.ALLOWED_EXTENSIONS)}",
            )

        # Check file exists
        if not path.exists():
            return False, f"File not found: {file_path}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > ImportValidator.MAX_FILE_SIZE:
            return (
                False,
                f"File too large. Maximum size: {ImportValidator.MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        if file_size == 0:
            return False, "File is empty"

        return True, None

    @staticmethod
    def validate_file_content(
        file_path: str, entity: ExportEntity
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Validate file content for malicious inputs and format.

        Returns:
            (is_valid, list_of_errors)
        """
        errors: list[dict[str, Any]] = []
        path = Path(file_path)
        extension = path.suffix.lower()

        try:
            if extension == ".csv":
                errors = ImportValidator._validate_csv_content(file_path, entity)
            elif extension == ".json":
                errors = ImportValidator._validate_json_content(file_path, entity)
            else:
                errors.append({"message": f"Unsupported file format: {extension}"})
        except Exception as e:
            logger.error(f"Error validating file content: {e}", exc_info=True)
            errors.append({"message": f"Error reading file: {str(e)}"})

        return len(errors) == 0, errors

    @staticmethod
    def _validate_csv_content(file_path: str, entity: ExportEntity) -> list[dict[str, Any]]:
        """Validate CSV file content."""
        errors: list[dict[str, Any]] = []
        required_fields = ImportValidator.REQUIRED_FIELDS.get(entity, [])

        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Check header row
                if not reader.fieldnames:
                    errors.append({"row": 0, "message": "CSV file has no header row"})
                    return errors

                # Check required fields exist
                missing_fields = [f for f in required_fields if f not in reader.fieldnames]
                if missing_fields:
                    errors.append(
                        {
                            "row": 0,
                            "message": f"Missing required fields: {', '.join(missing_fields)}",
                        }
                    )

                # Validate each data row
                row_num = 1  # Start at 1 (header is row 0)
                for row in reader:
                    row_errors = ImportValidator._validate_row(
                        row, row_num, entity, reader.fieldnames
                    )
                    errors.extend(row_errors)
                    row_num += 1

                # Check for empty file
                if row_num == 1:
                    errors.append({"row": 1, "message": "CSV file has no data rows"})

        except UnicodeDecodeError:
            errors.append({"row": 0, "message": "File encoding error. File must be UTF-8 encoded"})
        except csv.Error as e:
            errors.append({"row": 0, "message": f"CSV parsing error: {str(e)}"})
        except Exception as e:
            errors.append({"row": 0, "message": f"Error reading CSV file: {str(e)}"})

        return errors

    @staticmethod
    def _validate_json_content(file_path: str, entity: ExportEntity) -> list[dict[str, Any]]:
        """Validate JSON file content."""
        errors: list[dict[str, Any]] = []
        ImportValidator.REQUIRED_FIELDS.get(entity, [])

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # If single object, wrap in list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                errors.append({"row": 0, "message": "JSON must be an array or object"})
                return errors

            # Validate each record
            for idx, record in enumerate(data, start=1):
                if not isinstance(record, dict):
                    errors.append({"row": idx, "message": "Record must be an object"})
                    continue

                row_errors = ImportValidator._validate_row(record, idx, entity, list(record.keys()))
                errors.extend(row_errors)

        except json.JSONDecodeError as e:
            errors.append({"row": 0, "message": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            errors.append({"row": 0, "message": f"Error reading JSON file: {str(e)}"})

        return errors

    @staticmethod
    def _validate_row(
        row: dict[str, Any], row_num: int, entity: ExportEntity, available_fields: list[str]
    ) -> list[dict[str, Any]]:
        """Validate a single row of data."""
        errors: list[dict[str, Any]] = []
        required_fields = ImportValidator.REQUIRED_FIELDS.get(entity, [])

        # Check required fields have values
        for field in required_fields:
            if field not in available_fields:
                continue  # Already checked at file level
            value = row.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                errors.append(
                    {
                        "row": row_num,
                        "field": field,
                        "message": f"Required field '{field}' is missing or empty",
                    }
                )

        # Validate field types and values
        for field, value in row.items():
            if value is None or value == "":
                continue  # Empty values are allowed (except for required fields)

            # Check for malicious content (basic checks)
            if isinstance(value, str):
                # Check for SQL injection patterns
                sql_patterns = ["';", "--", "/*", "*/", "xp_", "sp_", "exec", "union", "select"]
                value_lower = value.lower()
                for pattern in sql_patterns:
                    if pattern in value_lower:
                        errors.append(
                            {
                                "row": row_num,
                                "field": field,
                                "message": f"Potentially malicious content detected in field '{field}'",
                            }
                        )
                        break

                # Check for script injection
                script_patterns = ["<script", "javascript:", "onerror=", "onclick="]
                for pattern in script_patterns:
                    if pattern in value_lower:
                        errors.append(
                            {
                                "row": row_num,
                                "field": field,
                                "message": f"Potentially malicious script content in field '{field}'",
                            }
                        )
                        break

                # Validate field-specific formats
                if field == "amount":
                    try:
                        float(value)
                    except ValueError:
                        errors.append(
                            {
                                "row": row_num,
                                "field": field,
                                "message": f"Field '{field}' must be a number",
                            }
                        )

                elif field == "date":
                    # Basic date format check (ISO format: YYYY-MM-DD)
                    import re

                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                        errors.append(
                            {
                                "row": row_num,
                                "field": field,
                                "message": f"Field '{field}' must be in YYYY-MM-DD format",
                            }
                        )

                elif field == "id":
                    # ID field is optional and can be any string format
                    # Empty ID is OK (will generate new UUID)
                    # Non-empty ID is accepted as-is (could be external reference)
                    # No validation needed for ID format
                    pass

            elif field == "amount" and not isinstance(value, (int, float)):
                errors.append(
                    {"row": row_num, "field": field, "message": f"Field '{field}' must be a number"}
                )

        return errors

    @staticmethod
    async def validate_import_file(
        file_path: str, entity: ExportEntity
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Complete validation of an import file.

        Returns:
            (is_valid, list_of_errors)
        """
        errors: list[dict[str, Any]] = []

        # Phase 1: File format validation
        is_valid, error_msg = ImportValidator.validate_file_format(file_path)
        if not is_valid:
            errors.append({"row": 0, "message": error_msg})
            return False, errors

        # Phase 2: Content validation
        is_valid, content_errors = ImportValidator.validate_file_content(file_path, entity)
        errors.extend(content_errors)

        return len(errors) == 0, errors
