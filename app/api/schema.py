"""API routes for schema discovery."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dto import (
    SchemaEntity,
    SchemaField,
    SchemaRelationship,
    SchemaRelationshipField,
    SchemaResponse,
)
from app.auth.backend import get_current_client_id
from app.core.logging import get_logger
from app.domain.entities import ExportEntity

logger = get_logger(__name__)
router = APIRouter(prefix="/schema", tags=["schema"])


# Define the schema for each entity
# In a real implementation, this could be loaded from database metadata or configuration
ENTITY_SCHEMAS: dict[str, SchemaEntity] = {
    ExportEntity.BILL.value: SchemaEntity(
        name="bill",
        label="Bills",
        description="Bills represent invoices received from vendors",
        fields=[
            SchemaField(name="id", type="uuid", label="ID", required=False),
            SchemaField(name="external_id", type="string", label="External ID", required=False),
            SchemaField(name="amount", type="number", label="Amount", required=True),
            SchemaField(name="date", type="date", label="Date", required=True),
            SchemaField(name="status", type="string", label="Status", required=False),
            SchemaField(name="description", type="string", label="Description", required=False),
            SchemaField(name="currency", type="string", label="Currency", required=False),
            SchemaField(name="vendor_id", type="uuid", label="Vendor ID", required=False),
            SchemaField(name="project_id", type="uuid", label="Project ID", required=False),
        ],
        relationships=[
            SchemaRelationship(
                name="vendor",
                label="Vendor",
                entity="vendor",
                type="many_to_one",
                fields=[
                    SchemaRelationshipField(name="name", type="string", label="Vendor Name"),
                    SchemaRelationshipField(name="email", type="string", label="Vendor Email"),
                ],
            ),
            SchemaRelationship(
                name="project",
                label="Project",
                entity="project",
                type="many_to_one",
                fields=[
                    SchemaRelationshipField(name="code", type="string", label="Project Code"),
                    SchemaRelationshipField(name="name", type="string", label="Project Name"),
                ],
            ),
        ],
    ),
    ExportEntity.INVOICE.value: SchemaEntity(
        name="invoice",
        label="Invoices",
        description="Invoices represent bills sent to customers",
        fields=[
            SchemaField(name="id", type="uuid", label="ID", required=False),
            SchemaField(name="external_id", type="string", label="External ID", required=False),
            SchemaField(name="amount", type="number", label="Amount", required=True),
            SchemaField(name="date", type="date", label="Date", required=True),
            SchemaField(name="status", type="string", label="Status", required=False),
            SchemaField(name="description", type="string", label="Description", required=False),
            SchemaField(name="currency", type="string", label="Currency", required=False),
            SchemaField(name="customer_id", type="uuid", label="Customer ID", required=False),
            SchemaField(name="project_id", type="uuid", label="Project ID", required=False),
        ],
        relationships=[
            SchemaRelationship(
                name="project",
                label="Project",
                entity="project",
                type="many_to_one",
                fields=[
                    SchemaRelationshipField(name="code", type="string", label="Project Code"),
                    SchemaRelationshipField(name="name", type="string", label="Project Name"),
                ],
            ),
        ],
    ),
    ExportEntity.VENDOR.value: SchemaEntity(
        name="vendor",
        label="Vendors",
        description="Vendors are suppliers or service providers",
        fields=[
            SchemaField(name="id", type="uuid", label="ID", required=False),
            SchemaField(name="external_id", type="string", label="External ID", required=False),
            SchemaField(name="name", type="string", label="Name", required=True),
            SchemaField(name="email", type="string", label="Email", required=False),
            SchemaField(name="phone", type="string", label="Phone", required=False),
            SchemaField(name="address", type="string", label="Address", required=False),
        ],
        relationships=[],
    ),
    ExportEntity.PROJECT.value: SchemaEntity(
        name="project",
        label="Projects",
        description="Projects for organizing work and tracking costs",
        fields=[
            SchemaField(name="id", type="uuid", label="ID", required=False),
            SchemaField(name="external_id", type="string", label="External ID", required=False),
            SchemaField(name="code", type="string", label="Code", required=True),
            SchemaField(name="name", type="string", label="Name", required=True),
            SchemaField(name="description", type="string", label="Description", required=False),
            SchemaField(name="status", type="string", label="Status", required=False),
        ],
        relationships=[],
    ),
}


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
