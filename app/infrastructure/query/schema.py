"""Schema definitions for allowed fields and joins."""

from app.domain.entities import ExportEntity

# Allowed fields for each entity
ENTITY_FIELDS: dict[ExportEntity, set[str]] = {
    ExportEntity.BILL: {
        "id",
        "external_id",
        "amount",
        "date",
        "due_date",
        "description",
        "currency",
        "vendor_id",
        "project_id",
        "status",
        "created_at",
        "updated_at",
    },
    ExportEntity.INVOICE: {
        "id",
        "external_id",
        "amount",
        "date",
        "due_date",
        "description",
        "currency",
        "vendor_id",
        "customer_id",
        "project_id",
        "status",
        "created_at",
        "updated_at",
    },
    ExportEntity.VENDOR: {
        "id",
        "external_id",
        "name",
        "email",
        "phone",
        "address",
        "created_at",
        "updated_at",
    },
    ExportEntity.PROJECT: {
        "id",
        "external_id",
        "code",
        "name",
        "description",
        "status",
        "created_at",
        "updated_at",
    },
}

# Allowed nested field paths (entity.relation.field)
NESTED_FIELDS: dict[ExportEntity, dict[str, set[str]]] = {
    ExportEntity.BILL: {
        "vendor": {"id", "name", "email"},
        "project": {"id", "code", "name"},
    },
    ExportEntity.INVOICE: {
        "vendor": {"id", "name", "email"},
        "project": {"id", "code", "name"},
    },
    ExportEntity.VENDOR: {
        "project": {"id", "code", "name"},
    },
    ExportEntity.PROJECT: {},
}

# Allowed join paths: (from_entity, to_entity) -> join condition info
ALLOWED_JOINS: dict[tuple[ExportEntity, str], tuple[ExportEntity, str]] = {
    (ExportEntity.BILL, "vendor"): (ExportEntity.VENDOR, "id"),
    (ExportEntity.BILL, "project"): (ExportEntity.PROJECT, "id"),
    (ExportEntity.INVOICE, "vendor"): (ExportEntity.VENDOR, "id"),
    (ExportEntity.INVOICE, "project"): (ExportEntity.PROJECT, "id"),
    (ExportEntity.VENDOR, "project"): (ExportEntity.PROJECT, "id"),
}


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
