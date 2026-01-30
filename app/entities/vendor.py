"""Vendor entity definition."""

from app.entities._registry import EntityDefinition, FieldDef, RelationshipDef, registry

vendor = EntityDefinition(
    name="vendor",
    label="Vendors",
    description="Vendors are suppliers or service providers",
    fields=[
        FieldDef(name="id", type="uuid", label="ID"),
        FieldDef(name="external_id", type="string", label="External ID"),
        FieldDef(name="name", type="string", label="Name", required=True),
        FieldDef(name="email", type="string", label="Email"),
        FieldDef(name="phone", type="string", label="Phone"),
        FieldDef(name="address", type="string", label="Address"),
        FieldDef(name="created_at", type="datetime", label="Created At"),
        FieldDef(name="updated_at", type="datetime", label="Updated At"),
    ],
    relationships=[
        RelationshipDef(
            name="project",
            entity="project",
            type="many_to_one",
            foreign_key="project_id",
            fields=[
                FieldDef(name="id", type="uuid", label="Project ID"),
                FieldDef(name="code", type="string", label="Project Code"),
                FieldDef(name="name", type="string", label="Project Name"),
            ],
        ),
    ],
    required_fields=["name"],
)

registry.register(vendor)
