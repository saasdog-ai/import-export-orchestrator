"""Centralized entity registry for schema, validation, and query configuration."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.domain.entities import ExportEntity

# Type alias for custom validator functions.
# Signature: (row: dict, row_num: int, errors: list[dict]) -> None
# Validators append errors to the mutable errors list.
# Each error should be: {"row": row_num, "field": field_name, "message": error_message}
ValidatorFunc = Callable[[dict[str, Any], int, list[dict[str, Any]]], None]


@dataclass
class FieldDef:
    """Definition of a single field on an entity."""

    name: str
    type: str
    label: str
    required: bool = False
    default: Any = None


@dataclass
class RelationshipDef:
    """Definition of a relationship between entities."""

    name: str
    entity: str
    type: str
    foreign_key: str
    target_key: str = "id"
    fields: list[FieldDef] = field(default_factory=list)


@dataclass
class EntityDefinition:
    """Complete definition of an entity for the registry."""

    name: str
    label: str
    description: str
    fields: list[FieldDef]
    relationships: list[RelationshipDef] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    match_key: str = "external_id"
    date_fields: set[str] = field(default_factory=set)
    decimal_fields: set[str] = field(default_factory=set)
    validators: list[ValidatorFunc] = field(default_factory=list)


class EntityRegistry:
    """Central registry for all entity definitions.

    Provides auto-generated schema, field, join, and validation
    metadata from a single EntityDefinition per entity.
    """

    def __init__(self) -> None:
        self._entities: dict[str, EntityDefinition] = {}

    def register(self, definition: EntityDefinition) -> None:
        """Register an entity definition."""
        self._entities[definition.name] = definition

    def get(self, name: str) -> EntityDefinition | None:
        """Get an entity definition by name."""
        return self._entities.get(name)

    def list_all(self) -> list[EntityDefinition]:
        """Return all registered entity definitions."""
        return list(self._entities.values())

    def get_names(self) -> list[str]:
        """Return all registered entity names."""
        return list(self._entities.keys())

    # ------------------------------------------------------------------
    # Auto-generation methods used by consumers
    # ------------------------------------------------------------------

    def get_entity_schemas(self) -> dict[str, Any]:
        """Generate ENTITY_SCHEMAS dict consumed by app.api.schema.

        Returns a dict keyed by entity name whose values are
        SchemaEntity-compatible dicts.
        """
        from app.api.dto import (
            SchemaEntity,
            SchemaField,
            SchemaRelationship,
            SchemaRelationshipField,
        )

        schemas: dict[str, SchemaEntity] = {}
        for defn in self._entities.values():
            schema_fields = [
                SchemaField(
                    name=f.name,
                    type=f.type,
                    label=f.label,
                    required=f.required,
                )
                for f in defn.fields
            ]
            schema_rels = [
                SchemaRelationship(
                    name=r.name,
                    label=r.name.capitalize(),
                    entity=r.entity,
                    type=r.type,
                    fields=[
                        SchemaRelationshipField(
                            name=rf.name,
                            type=rf.type,
                            label=rf.label,
                        )
                        for rf in r.fields
                    ],
                )
                for r in defn.relationships
            ]
            schemas[defn.name] = SchemaEntity(
                name=defn.name,
                label=defn.label,
                description=defn.description,
                fields=schema_fields,
                relationships=schema_rels,
            )
        return schemas

    def get_entity_fields(self) -> dict[ExportEntity, set[str]]:
        """Generate ENTITY_FIELDS dict consumed by query/schema.py."""
        result: dict[ExportEntity, set[str]] = {}
        for defn in self._entities.values():
            entity = ExportEntity(defn.name)
            result[entity] = {f.name for f in defn.fields}
        return result

    def get_nested_fields(self) -> dict[ExportEntity, dict[str, set[str]]]:
        """Generate NESTED_FIELDS dict consumed by query/schema.py."""
        result: dict[ExportEntity, dict[str, set[str]]] = {}
        for defn in self._entities.values():
            entity = ExportEntity(defn.name)
            nested: dict[str, set[str]] = {}
            for rel in defn.relationships:
                rel_defn = self._entities.get(rel.entity)
                if rel_defn:
                    nested[rel.name] = {rf.name for rf in rel.fields}
            result[entity] = nested
        return result

    def get_allowed_joins(self) -> dict[tuple[ExportEntity, str], tuple[ExportEntity, str]]:
        """Generate ALLOWED_JOINS dict consumed by query/schema.py."""
        result: dict[tuple[ExportEntity, str], tuple[ExportEntity, str]] = {}
        for defn in self._entities.values():
            entity = ExportEntity(defn.name)
            for rel in defn.relationships:
                target_entity = ExportEntity(rel.entity)
                result[(entity, rel.name)] = (target_entity, rel.target_key)
        return result

    def get_required_fields(self) -> dict[ExportEntity, list[str]]:
        """Generate REQUIRED_FIELDS dict consumed by import_validator.py."""
        result: dict[ExportEntity, list[str]] = {}
        for defn in self._entities.values():
            entity = ExportEntity(defn.name)
            result[entity] = list(defn.required_fields)
        return result

    def get_validators(self) -> dict[ExportEntity, list[ValidatorFunc]]:
        """Generate VALIDATORS dict consumed by import_validator.py."""
        result: dict[ExportEntity, list[ValidatorFunc]] = {}
        for defn in self._entities.values():
            entity = ExportEntity(defn.name)
            result[entity] = list(defn.validators)
        return result


# Module-level singleton
registry = EntityRegistry()
