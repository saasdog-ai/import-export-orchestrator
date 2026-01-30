"""Project entity definition."""

from app.entities._registry import EntityDefinition, FieldDef, registry

project = EntityDefinition(
    name="project",
    label="Projects",
    description="Projects for organizing work and tracking costs",
    fields=[
        FieldDef(name="id", type="uuid", label="ID"),
        FieldDef(name="external_id", type="string", label="External ID"),
        FieldDef(name="code", type="string", label="Code", required=True),
        FieldDef(name="name", type="string", label="Name", required=True),
        FieldDef(name="description", type="string", label="Description"),
        FieldDef(name="status", type="string", label="Status"),
        FieldDef(name="created_at", type="datetime", label="Created At"),
        FieldDef(name="updated_at", type="datetime", label="Updated At"),
    ],
    required_fields=["code", "name"],
    date_fields={"start_date", "end_date"},
    decimal_fields={"budget"},
)

registry.register(project)
