"""Schema definitions for allowed fields and joins."""

from app.domain.entities import ExportEntity
from app.entities import registry

# All field/join metadata is auto-generated from the centralized entity registry
ENTITY_FIELDS: dict[ExportEntity, set[str]] = registry.get_entity_fields()
NESTED_FIELDS: dict[ExportEntity, dict[str, set[str]]] = registry.get_nested_fields()
ALLOWED_JOINS: dict[tuple[ExportEntity, str], tuple[ExportEntity, str]] = (
    registry.get_allowed_joins()
)


def validate_field_path(entity: ExportEntity, field_path: str) -> bool:
    """Validate that a field path is allowed for the entity."""
    if "." not in field_path:
        # Simple field
        return field_path in ENTITY_FIELDS.get(entity, set())

    # Nested field path (e.g., "vendor.name")
    parts = field_path.split(".")
    if len(parts) != 2:
        return False

    relation, field = parts

    # Check if relation is allowed and field exists on that relation
    nested_fields = NESTED_FIELDS.get(entity, {})
    if relation not in nested_fields:
        return False

    return field in nested_fields[relation]


def get_allowed_fields(entity: ExportEntity) -> set[str]:
    """Get all allowed fields for an entity (simple + nested)."""
    fields = set(ENTITY_FIELDS.get(entity, set()))
    nested = NESTED_FIELDS.get(entity, {})
    for relation, relation_fields in nested.items():
        for field in relation_fields:
            fields.add(f"{relation}.{field}")
    return fields
