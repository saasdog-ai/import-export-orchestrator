"""Entity definitions and registry.

Importing this module triggers registration of all entity definitions.
"""

# Import entity modules to trigger registration
from app.entities import bill, invoice, project, vendor  # noqa: F401
from app.entities._registry import (
    EntityDefinition,
    EntityRegistry,
    FieldDef,
    RelationshipDef,
    registry,
)

__all__ = [
    "EntityDefinition",
    "EntityRegistry",
    "FieldDef",
    "RelationshipDef",
    "registry",
]
