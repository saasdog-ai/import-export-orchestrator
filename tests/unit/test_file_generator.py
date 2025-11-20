"""Unit tests for file generator."""

import os
import tempfile

from app.infrastructure.storage.file_generator import FileGenerator


def test_generate_csv_file():
    """Test CSV file generation."""
    data = [
        {"id": "1", "amount": 100.0, "date": "2024-01-01"},
        {"id": "2", "amount": 200.0, "date": "2024-01-02"},
    ]
    fields = ["id", "amount", "date"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)
        assert file_path.endswith(".csv")

        # Read and verify content
        with open(file_path) as f:
            content = f.read()
            assert "id,amount,date" in content
            assert "1,100.0,2024-01-01" in content


def test_generate_csv_file_nested_fields():
    """Test CSV file generation with nested fields."""
    data = [
        {"id": "1", "amount": 100.0, "vendor": {"name": "Acme"}},
    ]
    fields = ["id", "amount", "vendor.name"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)

        # Read and verify content
        with open(file_path) as f:
            content = f.read()
            assert "vendor.name" in content


def test_generate_json_file():
    """Test JSON file generation."""
    data = [
        {"id": "1", "amount": 100.0, "date": "2024-01-01"},
        {"id": "2", "amount": 200.0, "date": "2024-01-02"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_json_file(data, tmpdir)
        assert os.path.exists(file_path)
        assert file_path.endswith(".json")

        # Read and verify content
        import json

        with open(file_path) as f:
            content = json.load(f)
            assert len(content) == 2
            assert content[0]["id"] == "1"


def test_get_nested_value():
    """Test nested value extraction."""
    data = {"vendor": {"name": "Acme", "address": {"city": "NYC"}}}

    assert FileGenerator._get_nested_value(data, "vendor.name") == "Acme"
    assert FileGenerator._get_nested_value(data, "vendor.address.city") == "NYC"
    assert FileGenerator._get_nested_value(data, "vendor.invalid") is None
    assert FileGenerator._get_nested_value(data, "invalid") is None


def test_get_file_extension():
    """Test file extension helper."""
    assert FileGenerator.get_file_extension("csv") == ".csv"
    assert FileGenerator.get_file_extension("json") == ".json"
    assert FileGenerator.get_file_extension("CSV") == ".csv"  # Case insensitive


def test_get_content_type():
    """Test content type helper."""
    assert FileGenerator.get_content_type("csv") == "text/csv"
    assert FileGenerator.get_content_type("json") == "application/json"
