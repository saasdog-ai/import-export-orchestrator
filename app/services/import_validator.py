"""Validation service for import files."""

import csv
import json
from pathlib import Path
from typing import Any

from app.core.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE
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
        error: dict[str, Any] = {"message": self.message}
        if self.row is not None:
            error["row"] = self.row
        if self.field is not None:
            error["field"] = self.field
        return error


class ImportValidator:
    """Service for validating import files before processing."""

    # Use constants from app.core.constants
    MAX_FILE_SIZE = MAX_FILE_SIZE
    ALLOWED_EXTENSIONS = ALLOWED_FILE_EXTENSIONS

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
                    fieldnames_list = list(reader.fieldnames) if reader.fieldnames else []
                    row_errors = ImportValidator._validate_row(
                        row, row_num, entity, fieldnames_list
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

    @staticmethod
    def apply_field_mappings(
        record: dict[str, Any], field_mappings: dict[str, str]
    ) -> dict[str, Any]:
        """
        Apply field mappings to a record, renaming source columns to target fields.

        Args:
            record: Original record with source column names
            field_mappings: Dictionary mapping source column names to target field names

        Returns:
            New record with target field names
        """
        if not field_mappings:
            return record

        mapped_record: dict[str, Any] = {}
        for source_col, value in record.items():
            # If there's a mapping for this column, use the target name
            target_field = field_mappings.get(source_col, source_col)
            mapped_record[target_field] = value

        return mapped_record

    @staticmethod
    async def preview_with_validation(
        file_path: str,
        entity: ExportEntity,
        field_mappings: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Preview import file with validation status for each record.

        This method reads the entire file, applies field mappings, validates each row,
        and returns all records with their validation status.

        Args:
            file_path: Path to the import file
            entity: Entity type to validate against
            field_mappings: Optional dictionary mapping source column names to target fields

        Returns:
            Dictionary containing:
                - file_path: Path to the file
                - entity: Entity type
                - total_records: Total number of records
                - valid_count: Number of valid records
                - invalid_count: Number of invalid records
                - records: List of records with validation status
        """
        # First, validate file format
        is_valid, error_msg = ImportValidator.validate_file_format(file_path)
        if not is_valid:
            logger.error(f"File format validation failed: {error_msg}")
            raise ValueError(error_msg)

        path = Path(file_path)
        extension = path.suffix.lower()

        records: list[dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0

        try:
            if extension == ".csv":
                records, valid_count, invalid_count = await ImportValidator._preview_csv(
                    file_path, entity, field_mappings or {}
                )
            elif extension == ".json":
                records, valid_count, invalid_count = await ImportValidator._preview_json(
                    file_path, entity, field_mappings or {}
                )
            else:
                raise ValueError(f"Unsupported file format: {extension}")

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error previewing file: {e}", exc_info=True)
            raise ValueError(f"Error reading file: {str(e)}") from e

        return {
            "file_path": file_path,
            "entity": entity.value,
            "total_records": len(records),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "records": records,
        }

    @staticmethod
    async def _preview_csv(
        file_path: str,
        entity: ExportEntity,
        field_mappings: dict[str, str],
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Preview CSV file with validation."""
        records: list[dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0

        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames:
                    raise ValueError("CSV file has no header row")

                # Map the field names using mappings
                mapped_fieldnames = [field_mappings.get(fn, fn) for fn in reader.fieldnames]

                row_num = 1  # Start at 1 (header is row 0)
                for row in reader:
                    # Apply field mappings to the row
                    mapped_row = ImportValidator.apply_field_mappings(row, field_mappings)

                    # Validate the mapped row
                    row_errors = ImportValidator._validate_row(
                        mapped_row, row_num, entity, mapped_fieldnames
                    )

                    # Convert errors to the expected format
                    formatted_errors = [
                        {"field": e.get("field", ""), "message": e.get("message", "")}
                        for e in row_errors
                        if e.get("field")  # Only include field-level errors
                    ]

                    is_valid = len(formatted_errors) == 0
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1

                    records.append(
                        {
                            "row": row_num,
                            "data": mapped_row,
                            "is_valid": is_valid,
                            "errors": formatted_errors,
                        }
                    )

                    row_num += 1

        except UnicodeDecodeError as e:
            raise ValueError("File encoding error. File must be UTF-8 encoded") from e
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {str(e)}") from e

        return records, valid_count, invalid_count

    @staticmethod
    async def _preview_json(
        file_path: str,
        entity: ExportEntity,
        field_mappings: dict[str, str],
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Preview JSON file with validation."""
        records: list[dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # If single object, wrap in list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON must be an array or object")

            for idx, record in enumerate(data, start=1):
                if not isinstance(record, dict):
                    records.append(
                        {
                            "row": idx,
                            "data": {"_raw": str(record)},
                            "is_valid": False,
                            "errors": [{"field": "", "message": "Record must be an object"}],
                        }
                    )
                    invalid_count += 1
                    continue

                # Apply field mappings to the record
                mapped_record = ImportValidator.apply_field_mappings(record, field_mappings)
                mapped_fieldnames = list(mapped_record.keys())

                # Validate the mapped record
                row_errors = ImportValidator._validate_row(
                    mapped_record, idx, entity, mapped_fieldnames
                )

                # Convert errors to the expected format
                formatted_errors = [
                    {"field": e.get("field", ""), "message": e.get("message", "")}
                    for e in row_errors
                    if e.get("field")  # Only include field-level errors
                ]

                is_valid = len(formatted_errors) == 0
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                records.append(
                    {
                        "row": idx,
                        "data": mapped_record,
                        "is_valid": is_valid,
                        "errors": formatted_errors,
                    }
                )

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}") from e

        return records, valid_count, invalid_count
