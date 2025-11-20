"""Unit tests for file parser."""

import json
import tempfile
from pathlib import Path

import pytest

from app.infrastructure.storage.file_parser import FileParser


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


class TestFileParser:
    """Test cases for FileParser."""

    def test_parse_csv_file_success(self, temp_csv_file):
        """Test successful CSV file parsing."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",100.00,2024-01-01,Test bill\n")
            f.write(",200.50,2024-01-02,Another bill\n")

        records = FileParser.parse_csv_file(temp_csv_file)

        assert len(records) == 2
        assert records[0]["amount"] == "100.00"
        assert records[0]["date"] == "2024-01-01"
        assert records[0]["description"] == "Test bill"
        assert records[1]["amount"] == "200.50"

    def test_parse_csv_file_empty_strings_to_none(self, temp_csv_file):
        """Test that empty strings are converted to None."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date,description\n")
            f.write(",,2024-01-01,\n")

        records = FileParser.parse_csv_file(temp_csv_file)

        assert len(records) == 1
        assert records[0]["id"] is None
        assert records[0]["amount"] is None
        assert records[0]["description"] is None
        assert records[0]["date"] == "2024-01-01"

    def test_parse_csv_file_not_found(self):
        """Test CSV file parsing with non-existent file."""
        with pytest.raises(FileNotFoundError):
            FileParser.parse_csv_file("/nonexistent/file.csv")

    def test_parse_json_file_array(self, temp_json_file):
        """Test JSON file parsing with array."""
        data = [
            {"id": "", "amount": "100.00", "date": "2024-01-01"},
            {"id": "", "amount": "200.50", "date": "2024-01-02"},
        ]
        with open(temp_json_file, "w") as f:
            json.dump(data, f)

        records = FileParser.parse_json_file(temp_json_file)

        assert len(records) == 2
        assert records[0]["amount"] == "100.00"
        assert records[1]["amount"] == "200.50"

    def test_parse_json_file_single_object(self, temp_json_file):
        """Test JSON file parsing with single object (should be wrapped in array)."""
        data = {"id": "", "amount": "100.00", "date": "2024-01-01"}
        with open(temp_json_file, "w") as f:
            json.dump(data, f)

        records = FileParser.parse_json_file(temp_json_file)

        assert len(records) == 1
        assert isinstance(records, list)
        assert records[0]["amount"] == "100.00"

    def test_parse_json_file_not_found(self):
        """Test JSON file parsing with non-existent file."""
        with pytest.raises(FileNotFoundError):
            FileParser.parse_json_file("/nonexistent/file.json")

    def test_parse_file_csv(self, temp_csv_file):
        """Test parse_file with CSV extension."""
        with open(temp_csv_file, "w") as f:
            f.write("id,amount,date\n")
            f.write(",100.00,2024-01-01\n")

        records = FileParser.parse_file(temp_csv_file)

        assert len(records) == 1
        assert records[0]["amount"] == "100.00"

    def test_parse_file_json(self, temp_json_file):
        """Test parse_file with JSON extension."""
        data = [{"id": "", "amount": "100.00", "date": "2024-01-01"}]
        with open(temp_json_file, "w") as f:
            json.dump(data, f)

        records = FileParser.parse_file(temp_json_file)

        assert len(records) == 1
        assert records[0]["amount"] == "100.00"

    def test_parse_file_unsupported_format(self, tmp_path):
        """Test parse_file with unsupported format."""
        temp_file = tmp_path / "test.txt"
        temp_file.write_text("test content")

        with pytest.raises(ValueError) as exc_info:
            FileParser.parse_file(str(temp_file))

        assert "Unsupported file format" in str(exc_info.value)
