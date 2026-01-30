"""Invoice entity definition."""

from app.entities._registry import EntityDefinition, FieldDef, RelationshipDef, registry

invoice = EntityDefinition(
    name="invoice",
    label="Invoices",
    description="Invoices represent bills sent to customers",
    fields=[
        FieldDef(name="id", type="uuid", label="ID"),
        FieldDef(name="external_id", type="string", label="External ID"),
        FieldDef(name="amount", type="number", label="Amount", required=True),
        FieldDef(name="date", type="date", label="Date", required=True),
        FieldDef(name="due_date", type="date", label="Due Date"),
        FieldDef(name="status", type="string", label="Status"),
        FieldDef(name="description", type="string", label="Description"),
        FieldDef(name="currency", type="string", label="Currency"),
        FieldDef(name="vendor_id", type="uuid", label="Vendor ID"),
        FieldDef(name="customer_id", type="uuid", label="Customer ID"),
        FieldDef(name="project_id", type="uuid", label="Project ID"),
        FieldDef(name="created_at", type="datetime", label="Created At"),
        FieldDef(name="updated_at", type="datetime", label="Updated At"),
    ],
    relationships=[
        RelationshipDef(
            name="vendor",
            entity="vendor",
            type="many_to_one",
            foreign_key="contact_id",
            fields=[
                FieldDef(name="id", type="uuid", label="Vendor ID"),
                FieldDef(name="name", type="string", label="Vendor Name"),
                FieldDef(name="email", type="string", label="Vendor Email"),
            ],
        ),
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
    required_fields=["amount", "date"],
    date_fields={"issue_date", "due_date", "paid_on_date"},
    decimal_fields={"total_amount", "sub_total", "total_tax_amount", "balance", "exchange_rate"},
)

registry.register(invoice)
