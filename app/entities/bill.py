"""Bill entity definition."""

from datetime import datetime
from typing import Any

from app.entities._registry import EntityDefinition, FieldDef, RelationshipDef, registry


def validate_bill_amount_positive(
    row: dict[str, Any], row_num: int, errors: list[dict[str, Any]]
) -> None:
    """Validate that bill amount is positive."""
    amount = row.get("amount")
    if amount is not None and amount != "":
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "amount",
                        "message": "Amount must be greater than zero",
                    }
                )
        except (ValueError, TypeError):
            pass  # Type validation is handled elsewhere


def validate_bill_due_date_after_date(
    row: dict[str, Any], row_num: int, errors: list[dict[str, Any]]
) -> None:
    """Validate that due_date is after date if both are present."""
    date_str = row.get("date")
    due_date_str = row.get("due_date")

    if not date_str or not due_date_str:
        return

    try:
        # Parse ISO format dates (YYYY-MM-DD)
        date_val = datetime.strptime(str(date_str), "%Y-%m-%d")
        due_date_val = datetime.strptime(str(due_date_str), "%Y-%m-%d")

        if due_date_val < date_val:
            errors.append(
                {
                    "row": row_num,
                    "field": "due_date",
                    "message": "Due date cannot be before the bill date",
                }
            )
    except ValueError:
        pass  # Date format validation is handled elsewhere


bill = EntityDefinition(
    name="bill",
    label="Bills",
    description="Bills represent invoices received from vendors",
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
        FieldDef(name="project_id", type="uuid", label="Project ID"),
        FieldDef(name="created_at", type="datetime", label="Created At"),
        FieldDef(name="updated_at", type="datetime", label="Updated At"),
    ],
    relationships=[
        RelationshipDef(
            name="vendor",
            entity="vendor",
            type="many_to_one",
            foreign_key="vendor_id",
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
    date_fields={"date", "due_date", "paid_on_date"},
    decimal_fields={"amount"},
    validators=[validate_bill_amount_positive, validate_bill_due_date_after_date],
)

registry.register(bill)
