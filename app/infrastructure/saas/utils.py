"""Shared utility functions for SaaS client and handlers."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_date(value: Any) -> datetime | None:
    """Parse date from string, datetime, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        # Convert to naive UTC if timezone-aware
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            # Try ISO format first (handles both with and without timezone)
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(UTC).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            # Try parsing as date only (YYYY-MM-DD)
            try:
                dt = datetime.strptime(value, "%Y-%m-%d")
                return dt
            except ValueError:
                logger.warning(f"Failed to parse date: {value}")
                return None
    return None


def model_to_dict(model: Any, include_relations: bool = False) -> dict[str, Any]:
    """Convert SQLAlchemy model to dictionary."""
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        # Convert UUID to string
        if isinstance(value, UUID):
            value = str(value)
        # Convert Decimal to float
        elif isinstance(value, Decimal):
            value = float(value)
        # Convert datetime to ISO string
        elif isinstance(value, datetime):
            value = value.isoformat() + "Z"
        result[column.name] = value

    # Add client_id as string for compatibility
    result["client_id"] = str(result.get("client_id", ""))

    # Add id as string for compatibility
    if "id" in result:
        result["id"] = str(result["id"])

    # Map database field names to schema field names for compatibility
    field_mapping = {
        "email_address": "email",  # Vendor/Contact email
        "total_amount": "amount",  # Invoice amount
        "issue_date": "date",  # Invoice date
    }

    for db_field, schema_field in field_mapping.items():
        if db_field in result:
            result[schema_field] = result[db_field]

    return result
