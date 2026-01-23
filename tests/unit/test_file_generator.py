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


# ============================================================================
# Field Aliasing Tests
# ============================================================================


def test_generate_csv_with_aliased_fields():
    """Test CSV generation with aliased field names in headers.

    This simulates the flow from job_runner where:
    1. Query engine returns records with aliased keys
    2. output_fields contains the aliases
    3. File generator uses aliases as both headers and keys
    """
    # Data already has aliased keys (as returned by query engine)
    data = [
        {"Bill ID": "1", "Total Amount": 100.0, "Invoice Date": "2024-01-01"},
        {"Bill ID": "2", "Total Amount": 200.0, "Invoice Date": "2024-01-02"},
    ]
    # Fields are the aliases (output_fields from job_runner)
    fields = ["Bill ID", "Total Amount", "Invoice Date"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)

        # Read and verify content has aliased headers
        with open(file_path) as f:
            content = f.read()
            # Headers should be the aliased names
            assert "Bill ID,Total Amount,Invoice Date" in content
            # Values should be correct
            assert "1,100.0,2024-01-01" in content
            assert "2,200.0,2024-01-02" in content


def test_generate_csv_with_special_characters_in_aliases():
    """Test CSV generation with special characters in aliased field names."""
    data = [
        {"Amount ($)": 100.0, "Vendor/Supplier": "Acme Corp"},
        {"Amount ($)": 200.0, "Vendor/Supplier": "Tech Inc"},
    ]
    fields = ["Amount ($)", "Vendor/Supplier"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)

        with open(file_path) as f:
            content = f.read()
            # CSV should handle special characters in headers
            assert "Amount ($)" in content
            assert "Vendor/Supplier" in content


def test_generate_csv_mixed_aliased_and_unaliased():
    """Test CSV generation with mix of aliased and unaliased field names."""
    data = [
        {"id": "1", "Total Amount": 100.0, "date": "2024-01-01"},
        {"id": "2", "Total Amount": 200.0, "date": "2024-01-02"},
    ]
    fields = ["id", "Total Amount", "date"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)

        with open(file_path) as f:
            content = f.read()
            # Should have both original and aliased headers
            assert "id,Total Amount,date" in content


def test_generate_csv_with_nested_field_aliases():
    """Test CSV generation with aliased nested fields.

    When nested fields are aliased (e.g., vendor.name -> 'Vendor Name'),
    the query engine flattens and aliases them. The file generator
    receives records with the aliased keys.
    """
    # Data has aliased nested field (vendor.name -> Vendor Name)
    data = [
        {"id": "1", "Vendor Name": "Acme Corp", "Project Code": "PROJ-001"},
        {"id": "2", "Vendor Name": "Tech Inc", "Project Code": "PROJ-002"},
    ]
    fields = ["id", "Vendor Name", "Project Code"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_csv_file(data, fields, tmpdir)
        assert os.path.exists(file_path)

        with open(file_path) as f:
            content = f.read()
            # Headers should be the aliased names
            assert "id,Vendor Name,Project Code" in content
            assert "Acme Corp" in content
            assert "PROJ-001" in content


def test_generate_json_preserves_aliased_keys():
    """Test JSON generation preserves aliased field names."""
    data = [
        {"Bill ID": "1", "Total Amount": 100.0, "Vendor Name": "Acme"},
        {"Bill ID": "2", "Total Amount": 200.0, "Vendor Name": "Tech"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = FileGenerator.generate_json_file(data, tmpdir)
        assert os.path.exists(file_path)

        import json

        with open(file_path) as f:
            content = json.load(f)
            assert len(content) == 2
            # JSON should preserve aliased keys
            assert content[0]["Bill ID"] == "1"
            assert content[0]["Total Amount"] == 100.0
            assert content[0]["Vendor Name"] == "Acme"
