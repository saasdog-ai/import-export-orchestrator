"""API routes for schema discovery."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dto import (
    SchemaEntity,
    SchemaResponse,
)
from app.auth.backend import get_current_client_id
from app.core.logging import get_logger
from app.entities import registry

logger = get_logger(__name__)
router = APIRouter(prefix="/schema", tags=["schema"])


# Entity schemas are auto-generated from the centralized entity registry
ENTITY_SCHEMAS: dict[str, SchemaEntity] = registry.get_entity_schemas()


@router.get(
    "/entities",
    response_model=SchemaResponse,
    summary="Get entity schema",
    description="""
    Get the schema for all available entities.

    This endpoint returns metadata about all entities that can be exported or imported,
    including:
    - Entity name and label
    - Available fields with their types
    - Relationships to other entities (for exports with joins)

    Use this to dynamically build UIs for configuring exports and imports.
    """,
    responses={
        200: {
            "description": "Schema retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "entities": [
                            {
                                "name": "bill",
                                "label": "Bills",
                                "fields": [
                                    {"name": "id", "type": "uuid", "label": "ID"},
                                    {"name": "amount", "type": "number", "label": "Amount"},
                                ],
                                "relationships": [
                                    {
                                        "name": "vendor",
                                        "label": "Vendor",
                                        "entity": "vendor",
                                        "fields": [
                                            {
                                                "name": "name",
                                                "type": "string",
                                                "label": "Vendor Name",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def get_entity_schema(
    authenticated_client_id: UUID = Depends(get_current_client_id),
) -> SchemaResponse:
    """
    Get the schema for all available entities.

    Returns metadata about entities, their fields, and relationships.
    This is used by the UI to dynamically render export/import configuration forms.
    """
    # Log request
    logger.info(
        f"Schema request: client_id={authenticated_client_id}, entity_count={len(ENTITY_SCHEMAS)}"
    )

    # Return all entity schemas
    entities = list(ENTITY_SCHEMAS.values())

    # Log response
    logger.info(
        f"Schema response: client_id={authenticated_client_id}, entities_returned={len(entities)}"
    )

    return SchemaResponse(entities=entities)


@router.get(
    "/entities/{entity_name}",
    response_model=SchemaEntity,
    summary="Get single entity schema",
    description="Get the schema for a specific entity by name.",
    responses={
        200: {"description": "Entity schema retrieved successfully"},
        404: {"description": "Entity not found"},
    },
)
async def get_single_entity_schema(
    entity_name: str,
    authenticated_client_id: UUID = Depends(get_current_client_id),
) -> SchemaEntity:
    """
    Get the schema for a single entity by name.
    """
    logger.info(
        f"Single entity schema request: client_id={authenticated_client_id}, "
        f"entity_name={entity_name}"
    )

    if entity_name not in ENTITY_SCHEMAS:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_name}' not found. Available entities: {list(ENTITY_SCHEMAS.keys())}",
        )

    entity_schema = ENTITY_SCHEMAS[entity_name]

    logger.info(
        f"Single entity schema response: client_id={authenticated_client_id}, "
        f"entity_name={entity_name}, fields_count={len(entity_schema.fields)}, "
        f"relationships_count={len(entity_schema.relationships)}"
    )

    return entity_schema
