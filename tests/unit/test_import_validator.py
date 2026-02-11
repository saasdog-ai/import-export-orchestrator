"""Unit tests for import validator."""

import tempfile
from pathlib import Path

import pytest

from app.domain.entities import ExportEntity
from app.services.import_validator import ImportValidator


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)


class TestImportValidator:
    """Test cases for ImportValidator."""

    def test_validate_file_format_valid_csv(self, temp_csv_file):
        """Test file format validation for valid CSV."""
        # Create a valid CSV file
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",100.00,2024-01-01\n")

        is_valid, error = ImportValidator.validate_file_format(temp_csv_file)
        assert is_valid is True
        assert error is None

    def test_validate_file_format_invalid_extension(self, tmp_path):
        """Test file format validation for invalid extension."""
        temp_file = tmp_path / "test.txt"
        temp_file.write_text("test content")

        is_valid, error = ImportValidator.validate_file_format(str(temp_file))
        assert is_valid is False
        assert "Invalid file format" in error

    def test_validate_file_format_empty_file(self, temp_csv_file):
        """Test file format validation for empty file."""
        # Create empty file
        Path(temp_csv_file).touch()

        is_valid, error = ImportValidator.validate_file_format(temp_csv_file)
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_csv_content_valid(self, temp_csv_file):
        """Test CSV content validation for valid data."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,Test\n")
            f.write(",200.50,2024-01-02,Another test\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_csv_content_missing_required_fields(self, temp_csv_file):
        """Test CSV content validation for missing required fields."""
        with open(temp_csv_file, "w") as f:
            f.write("id,description\n")
            f.write(",Test\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Missing required fields" in e.get("message", "") for e in errors)

    def test_validate_csv_content_invalid_amount(self, temp_csv_file):
        """Test CSV content validation for invalid amount."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",invalid,2024-01-01\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "amount" and "number" in e.get("message", "").lower() for e in errors
        )

    def test_validate_csv_content_invalid_date(self, temp_csv_file):
        """Test CSV content validation for invalid date format."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",100.00,01-01-2024\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "date" and "YYYY-MM-DD" in e.get("message", "") for e in errors
        )

    def test_validate_csv_content_malicious_script(self, temp_csv_file):
        """Test CSV content validation for malicious script content."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,<script>alert('xss')</script>\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            "malicious" in e.get("message", "").lower() or "script" in e.get("message", "").lower()
            for e in errors
        )

    def test_validate_csv_content_sql_injection(self, temp_csv_file):
        """Test CSV content validation for SQL injection patterns."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,'; DROP TABLE bills; --\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any("malicious" in e.get("message", "").lower() for e in errors)

    def test_validate_csv_content_legitimate_business_names(self, temp_csv_file):
        """Test that legitimate business names with SQL keywords are NOT flagged."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,Union Pacific Railroad\n")
            f.write(",200.00,2024-01-02,Select Staffing Services\n")
            f.write(",300.00,2024-01-03,Executive Solutions Inc\n")
            f.write(",400.00,2024-01-04,Credit Union of California\n")

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_csv_content_missing_required_field_value(self, temp_csv_file):
        """Test CSV content validation for missing required field value."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",,2024-01-01\n")  # Missing amount

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "amount" and "required" in e.get("message", "").lower()
            for e in errors
        )

    def test_validate_json_content_valid(self, temp_json_file):
        """Test JSON content validation for valid data."""
        import json

        data = [
            {"id": "", "amount": "100.00", "date": "2024-01-01", "description": "Test"},
            {"id": "", "amount": "200.50", "date": "2024-01-02", "description": "Another"},
        ]
        with open(temp_json_file, "w") as f:
            json.dump(data, f)

        is_valid, errors = ImportValidator.validate_file_content(temp_json_file, ExportEntity.BILL)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_json_content_invalid_format(self, temp_json_file):
        """Test JSON content validation for invalid JSON."""
        with open(temp_json_file, "w") as f:
            f.write("{ invalid json }")

        is_valid, errors = ImportValidator.validate_file_content(temp_json_file, ExportEntity.BILL)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Invalid JSON" in e.get("message", "") for e in errors)

    @pytest.mark.asyncio
    async def test_validate_import_file_valid(self, temp_csv_file):
        """Test complete import file validation for valid file."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,Test\n")

        is_valid, errors = await ImportValidator.validate_import_file(
            temp_csv_file, ExportEntity.BILL
        )
        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_import_file_invalid(self, temp_csv_file):
        """Test complete import file validation for invalid file."""
        with open(temp_csv_file, "w") as f:
            f.write("id,description\n")  # Missing required fields
            f.write(",Test\n")

        is_valid, errors = await ImportValidator.validate_import_file(
            temp_csv_file, ExportEntity.BILL
        )
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_row_required_fields(self):
        """Test row validation for required fields."""
        # Test with required fields in available_fields but missing values
        row = {"amount": "", "date": "", "description": "Test"}  # Missing amount and date values
        available_fields = ["amount", "date", "description"]
        errors = ImportValidator._validate_row(row, 1, ExportEntity.BILL, available_fields)

        assert len(errors) > 0
        assert any(e.get("field") == "amount" for e in errors)
        assert any(e.get("field") == "date" for e in errors)

    def test_validate_row_valid_data(self):
        """Test row validation for valid data."""
        row = {"amount": "100.00", "date": "2024-01-01", "description": "Test"}
        available_fields = ["amount", "date", "description"]
        errors = ImportValidator._validate_row(row, 1, ExportEntity.BILL, available_fields)

        assert len(errors) == 0

    def test_validate_row_invalid_amount_type(self):
        """Test row validation for invalid amount type."""
        row = {"amount": "not_a_number", "date": "2024-01-01"}
        available_fields = ["amount", "date"]
        errors = ImportValidator._validate_row(row, 1, ExportEntity.BILL, available_fields)

        assert len(errors) > 0
        assert any(
            e.get("field") == "amount" and "number" in e.get("message", "").lower() for e in errors
        )

    def test_custom_validator_amount_positive(self, temp_csv_file):
        """Test that the custom bill validator rejects negative amounts."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",-100.00,2024-01-01\n")  # Negative amount

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "amount" and "greater than zero" in e.get("message", "").lower()
            for e in errors
        )

    def test_custom_validator_amount_zero(self, temp_csv_file):
        """Test that the custom bill validator rejects zero amounts."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",0,2024-01-01\n")  # Zero amount

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "amount" and "greater than zero" in e.get("message", "").lower()
            for e in errors
        )

    def test_custom_validator_due_date_before_date(self, temp_csv_file):
        """Test that the custom bill validator rejects due_date before date."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,due_date\n")
            f.write(",100.00,2024-01-15,2024-01-01\n")  # due_date before date

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        assert any(
            e.get("field") == "due_date" and "before the bill date" in e.get("message", "").lower()
            for e in errors
        )

    def test_custom_validator_due_date_after_date_valid(self, temp_csv_file):
        """Test that the custom bill validator accepts due_date after date."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,due_date\n")
            f.write(",100.00,2024-01-01,2024-01-31\n")  # due_date after date

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is True
        assert len(errors) == 0

    def test_custom_validators_multiple_errors(self, temp_csv_file):
        """Test that multiple custom validators can report errors."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,due_date\n")
            f.write(",-50.00,2024-01-15,2024-01-01\n")  # Both negative and due_date before date

        is_valid, errors = ImportValidator.validate_file_content(temp_csv_file, ExportEntity.BILL)
        assert is_valid is False
        # Should have errors for both amount and due_date
        assert any(e.get("field") == "amount" for e in errors)
        assert any(e.get("field") == "due_date" for e in errors)
