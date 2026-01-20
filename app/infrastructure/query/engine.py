"""Query engine for translating DSL filters to SQLAlchemy expressions."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, not_, or_

from app.core.logging import get_logger
from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportFilter,
    ExportFilterGroup,
    ExportFilterOperator,
    LogicalOperator,
)
from app.infrastructure.db.database import Database
from app.infrastructure.query.schema import (
    validate_field_path,
)
from app.infrastructure.saas.client import SaaSApiClientInterface

logger = get_logger(__name__)


def resolve_relative_date(relative_value: str) -> datetime:
    """Resolve a relative date string to an actual datetime.

    Supports:
    - relative:last_7_days
    - relative:last_30_days
    - relative:last_90_days
    - relative:this_month
    - relative:last_month
    - relative:this_quarter
    - relative:this_year
    """
    now = datetime.now(UTC)

    if relative_value == "relative:last_7_days":
        return now - timedelta(days=7)
    elif relative_value == "relative:last_30_days":
        return now - timedelta(days=30)
    elif relative_value == "relative:last_90_days":
        return now - timedelta(days=90)
    elif relative_value == "relative:this_month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif relative_value == "relative:last_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = first_of_this_month - timedelta(days=1)
        return last_month.replace(day=1)
    elif relative_value == "relative:this_quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif relative_value == "relative:this_year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown relative date: {relative_value}")


class ExportQueryEngine:
    """Engine for building and executing safe SQLAlchemy queries from DSL."""

    def __init__(self, db: Database, saas_client: SaaSApiClientInterface):
        """Initialize query engine."""
        self.db = db
        self.saas_client = saas_client
        # Mock models for query building (in real implementation, these would be actual ORM models)
        self._mock_models: dict[ExportEntity, Any] = {}

    async def execute_export_query(self, config: ExportConfig, client_id: UUID) -> dict[str, Any]:
        """
        Execute an export query and return results.

        Args:
            config: Export configuration (entity, fields, filters, etc.)
            client_id: Client ID to filter data by (security: ensures data isolation)

        Returns:
            Dictionary with entity, count, records, limit, and offset
        """
        # Get source field names for validation and querying
        source_fields = config.get_source_fields()
        field_mappings = config.get_field_mappings()

        # Log field configuration
        aliased_fields = [f for f in config.fields if f.as_ is not None]
        logger.debug(
            f"Export query: entity={config.entity.value}, "
            f"fields={len(source_fields)}, aliased={len(aliased_fields)}, "
            f"client_id={client_id}"
        )
        if aliased_fields:
            alias_info = {f.field: f.as_ for f in aliased_fields}
            logger.debug(f"Field aliases: {alias_info}")

        # Validate all source fields
        for field in source_fields:
            if not validate_field_path(config.entity, field):
                raise ValueError(
                    f"Field '{field}' is not allowed for entity '{config.entity.value}'"
                )

        # Validate filters
        if config.filters:
            self._validate_filter_group(config.entity, config.filters)

        # Fetch data from SaaS API (main SaaS app)
        # SECURITY: Pass client_id to ensure only data owned by this client is returned
        # In production, this would call the actual SaaS API with client_id
        # For now, use the mock client which filters by client_id
        filters_dict = self._filters_to_dict(config.filters) if config.filters else {}
        all_data = await self.saas_client.fetch_data(
            config.entity, client_id=client_id, filters=filters_dict
        )

        # Apply filters (if SaaS client didn't apply them)
        filtered_data = self._apply_filters(all_data, config)

        # Apply sorting
        sorted_data = self._apply_sorting(filtered_data, config.sort)

        # Apply limit and offset
        total_count = len(sorted_data)
        paginated_data = sorted_data[
            config.offset : config.offset + (config.limit or len(sorted_data))
        ]

        # Select only requested fields, applying aliases from field_mappings
        selected_records = self._select_fields(
            paginated_data, source_fields, config.entity, field_mappings
        )

        return {
            "entity": config.entity.value,
            "count": total_count,
            "records": selected_records,
            "limit": config.limit,
            "offset": config.offset,
        }

    def _validate_filter_group(self, entity: ExportEntity, group: ExportFilterGroup) -> None:
        """Validate a filter group recursively."""
        for filter_item in group.filters:
            if not validate_field_path(entity, filter_item.field):
                raise ValueError(
                    f"Field '{filter_item.field}' is not allowed for entity '{entity.value}'"
                )

        for sub_group in group.groups:
            self._validate_filter_group(entity, sub_group)

    def _build_query(self, config: ExportConfig) -> Any:
        """Build SQLAlchemy query from config."""
        # In a real implementation, this would:
        # 1. Select the base model for the entity
        # 2. Add joins based on nested field paths
        # 3. Apply filters using SQLAlchemy expressions
        # 4. Apply sorting
        # 5. Apply limit/offset

        # For now, return a placeholder
        # In real implementation, this would build actual SQLAlchemy select() statements
        return None

    def _build_filter_expression(self, entity: ExportEntity, filter_item: ExportFilter) -> Any:
        """Build SQLAlchemy filter expression from a filter."""
        # In a real implementation, this would:
        # 1. Parse field path (e.g., "vendor.name" -> (Vendor, "name"))
        # 2. Get the appropriate column
        # 3. Apply the operator using SQLAlchemy methods

        # Placeholder - would return actual SQLAlchemy expressions
        # Example structure:
        # if filter_item.operator == ExportFilterOperator.EQ:
        #     return column == filter_item.value
        # elif filter_item.operator == ExportFilterOperator.IN:
        #     return column.in_(filter_item.value)
        # etc.
        return None

    def _combine_filters(self, operator: LogicalOperator, expressions: list[Any]) -> Any:
        """Combine filter expressions with logical operator."""
        if not expressions:
            return None

        if operator == LogicalOperator.AND:
            return and_(*expressions)
        elif operator == LogicalOperator.OR:
            return or_(*expressions)
        elif operator == LogicalOperator.NOT:
            if len(expressions) != 1:
                raise ValueError("NOT operator requires exactly one expression")
            return not_(expressions[0])
        else:
            raise ValueError(f"Unknown logical operator: {operator}")

    def _filters_to_dict(self, filter_group: ExportFilterGroup) -> dict[str, Any]:
        """Convert filter group to a simple dict for SaaS API (simplified)."""
        # In production, this would be more sophisticated
        # For now, return a basic structure
        result = {}
        for filter_item in filter_group.filters:
            result[filter_item.field] = {
                "operator": filter_item.operator.value,
                "value": filter_item.value,
            }
        return result

    def _apply_filters(
        self, data: list[dict[str, Any]], config: ExportConfig
    ) -> list[dict[str, Any]]:
        """Apply filters to data (in-memory filtering for mock data)."""
        if not config.filters:
            return data

        filtered = []
        for record in data:
            if self._matches_filters(record, config.filters, config.entity):
                filtered.append(record)

        return filtered

    def _matches_filters(
        self, record: dict[str, Any], filter_group: ExportFilterGroup, entity: ExportEntity
    ) -> bool:
        """Check if a record matches the filter group."""
        results = []

        # Check individual filters
        for filter_item in filter_group.filters:
            field_value = self._get_nested_value(record, filter_item.field)
            matches = self._evaluate_filter(field_value, filter_item.operator, filter_item.value)
            results.append(matches)

        # Check sub-groups
        for sub_group in filter_group.groups:
            matches = self._matches_filters(record, sub_group, entity)
            results.append(matches)

        # Combine results based on operator
        if filter_group.operator == LogicalOperator.AND:
            return all(results)
        elif filter_group.operator == LogicalOperator.OR:
            return any(results)
        elif filter_group.operator == LogicalOperator.NOT:
            return not any(results)
        else:
            return True

    def _evaluate_filter(
        self, field_value: Any, operator: ExportFilterOperator, filter_value: Any
    ) -> bool:
        """Evaluate a single filter condition."""
        if field_value is None:
            return False

        # Resolve relative date values
        if isinstance(filter_value, str) and filter_value.startswith("relative:"):
            try:
                filter_value = resolve_relative_date(filter_value)
            except ValueError as e:
                logger.warning(f"Failed to resolve relative date: {e}")
                return False

        # Parse field_value if it's a date string for comparison with datetime
        if isinstance(filter_value, datetime) and isinstance(field_value, str):
            try:
                # Try to parse ISO format datetime string
                field_value = datetime.fromisoformat(field_value.replace("Z", "+00:00"))
            except ValueError:
                pass

        try:
            if operator == ExportFilterOperator.EQ:
                return field_value == filter_value
            elif operator == ExportFilterOperator.NE:
                return field_value != filter_value
            elif operator == ExportFilterOperator.LT:
                return field_value < filter_value
            elif operator == ExportFilterOperator.LTE:
                return field_value <= filter_value
            elif operator == ExportFilterOperator.GT:
                return field_value > filter_value
            elif operator == ExportFilterOperator.GTE:
                return field_value >= filter_value
            elif operator == ExportFilterOperator.IN:
                return field_value in filter_value
            elif operator == ExportFilterOperator.BETWEEN:
                return filter_value[0] <= field_value <= filter_value[1]
            elif operator == ExportFilterOperator.CONTAINS:
                return str(filter_value).lower() in str(field_value).lower()
            elif operator == ExportFilterOperator.STARTSWITH:
                return str(field_value).startswith(str(filter_value))
            elif operator == ExportFilterOperator.ENDSWITH:
                return str(field_value).endswith(str(filter_value))
            elif operator == ExportFilterOperator.ILIKE:
                return str(filter_value).lower() in str(field_value).lower()
            else:
                return True
        except (TypeError, ValueError):
            return False

    def _get_nested_value(self, data: dict[str, Any], field_path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        parts = field_path.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value

    def _apply_sorting(
        self, data: list[dict[str, Any]], sort: list[dict[str, str]] | None
    ) -> list[dict[str, Any]]:
        """Apply sorting to data with support for mixed sort directions."""
        if not sort:
            return data

        def sort_key(record: dict[str, Any]) -> tuple:
            """Generate sort key from record, handling mixed sort directions."""
            keys = []
            for sort_item in sort:
                field = sort_item.get("field", "")
                direction = sort_item.get("direction", "asc").lower()
                value = self._get_nested_value(record, field)
                # Handle None values - put them at the end
                if value is None:
                    # Use a value that sorts last for ascending, first for descending
                    value = float("inf") if direction == "asc" else float("-inf")
                else:
                    # For descending fields, negate numeric values
                    if direction == "desc":
                        if isinstance(value, (int, float)):
                            value = -value  # Negate for descending numeric sort
                        # For strings and other types, we'll handle in post-processing
                keys.append((value, direction == "desc"))  # Store direction with value
            return tuple(keys)

        try:
            # Sort the data
            sorted_data = sorted(
                data,
                key=lambda r: tuple(
                    (-v if isinstance(v, (int, float)) and desc else v)
                    if v is not None
                    else (float("inf") if not desc else float("-inf"))
                    for (v, desc) in [
                        (
                            self._get_nested_value(r, s.get("field", "")),
                            s.get("direction", "asc").lower() == "desc",
                        )
                        for s in sort
                    ]
                ),
            )

            # Post-process: For string fields that are descending, we need to reverse
            # Check if we have any descending string fields
            has_desc_string = False
            for sort_item in sort:
                if sort_item.get("direction", "asc").lower() == "desc":
                    if sorted_data:
                        sample_value = self._get_nested_value(
                            sorted_data[0], sort_item.get("field", "")
                        )
                        if isinstance(sample_value, str):
                            has_desc_string = True
                            break

            if has_desc_string:
                # For descending string fields, we need a more complex approach
                # Group by all sort fields up to the first descending string field
                # Then sort each group
                from collections import defaultdict

                # Find first descending string field index
                first_desc_string_idx = None
                for i, sort_item in enumerate(sort):
                    if sort_item.get("direction", "asc").lower() == "desc":
                        if sorted_data:
                            sample_value = self._get_nested_value(
                                sorted_data[0], sort_item.get("field", "")
                            )
                            if isinstance(sample_value, str):
                                first_desc_string_idx = i
                                break

                if first_desc_string_idx is not None:
                    # Group by all fields before the first descending string
                    groups = defaultdict(list)
                    for record in sorted_data:
                        group_key = tuple(
                            self._get_nested_value(record, sort[i].get("field", ""))
                            for i in range(first_desc_string_idx)
                        )
                        groups[group_key].append(record)

                    # Sort each group by the descending string field and subsequent fields
                    result = []
                    for group_key in sorted(groups.keys()):
                        group_records = groups[group_key]
                        # Sort this group by remaining fields
                        group_sorted = sorted(
                            group_records,
                            key=lambda r: tuple(
                                self._get_nested_value(r, s.get("field", ""))
                                if s.get("direction", "asc").lower() == "asc"
                                else (
                                    -v
                                    if isinstance(
                                        (v := self._get_nested_value(r, s.get("field", ""))),
                                        (int, float),
                                    )
                                    else v
                                )
                                for s in sort[first_desc_string_idx:]
                            ),
                        )
                        # Reverse if first remaining field is descending string
                        if sort[first_desc_string_idx].get("direction", "asc").lower() == "desc":
                            group_sorted.reverse()
                        result.extend(group_sorted)
                    return result

            return sorted_data
        except Exception as e:
            logger.warning(f"Failed to sort data: {e}")
            return data

    def _select_fields(
        self,
        data: list[dict[str, Any]],
        fields: list[str],
        entity: ExportEntity,
        field_mappings: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Select and format only the requested fields, applying aliases if provided."""
        result = []
        for record in data:
            selected_record = {}
            for field in fields:
                value = self._get_nested_value(record, field)
                # Use the mapped output name if provided, otherwise use original field name
                output_key = field_mappings.get(field, field) if field_mappings else field
                # For nested fields like "vendor.name", flatten to the field name
                # For simple fields, use as-is
                if "." in field:
                    # Use the mapped key or the full path (e.g., "vendor.name")
                    selected_record[output_key] = value
                else:
                    selected_record[output_key] = record.get(field)
            result.append(selected_record)
        return result
