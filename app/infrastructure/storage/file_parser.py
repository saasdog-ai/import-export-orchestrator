"""File parsing utilities for imports."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.logging import get_logger

logger = get_logger(__name__)


class FileParser:
    """Utility for parsing import files (CSV, JSON)."""

    @staticmethod
    def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a CSV file into a list of dictionaries.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of dictionaries, one per row
        """
        records = []
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert empty strings to None for optional fields
                cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
                records.append(cleaned_row)
        
        logger.info(f"Parsed {len(records)} records from CSV file: {file_path}")
        return records

    @staticmethod
    def parse_json_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a JSON file into a list of dictionaries.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of dictionaries
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # If data is a single object, wrap it in a list
        if isinstance(data, dict):
            data = [data]
        
        logger.info(f"Parsed {len(data)} records from JSON file: {file_path}")
        return data

    @staticmethod
    def parse_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a file (CSV or JSON) based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dictionaries
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == ".csv":
            return FileParser.parse_csv_file(file_path)
        elif extension == ".json":
            return FileParser.parse_json_file(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}. Supported: .csv, .json")

