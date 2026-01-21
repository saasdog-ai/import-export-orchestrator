"""Add external_id column to all sample tables for upsert support.

Revision ID: 004
Revises: 003
Create Date: 2026-01-20

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_external_id"
down_revision: str | None = "003_create_sample_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add external_id column to all sample tables."""
    # Add external_id to sample_vendors
    op.add_column(
        "sample_vendors",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_vendor_client_external_id",
        "sample_vendors",
        ["client_id", "external_id"],
    )
    op.create_index(
        "ix_vendor_external_id",
        "sample_vendors",
        ["client_id", "external_id"],
    )

    # Add external_id to sample_invoices
    op.add_column(
        "sample_invoices",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_invoice_client_external_id",
        "sample_invoices",
        ["client_id", "external_id"],
    )
    op.create_index(
        "ix_invoice_external_id",
        "sample_invoices",
        ["client_id", "external_id"],
    )

    # Add external_id to sample_bills
    op.add_column(
        "sample_bills",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_bill_client_external_id",
        "sample_bills",
        ["client_id", "external_id"],
    )
    op.create_index(
        "ix_bill_external_id",
        "sample_bills",
        ["client_id", "external_id"],
    )

    # Add external_id to sample_projects
    op.add_column(
        "sample_projects",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_project_client_external_id",
        "sample_projects",
        ["client_id", "external_id"],
    )
    op.create_index(
        "ix_project_external_id",
        "sample_projects",
        ["client_id", "external_id"],
    )


def downgrade() -> None:
    """Remove external_id column from all sample tables."""
    # Remove from sample_projects
    op.drop_index("ix_project_external_id", table_name="sample_projects")
    op.drop_constraint("uq_project_client_external_id", "sample_projects", type_="unique")
    op.drop_column("sample_projects", "external_id")

    # Remove from sample_bills
    op.drop_index("ix_bill_external_id", table_name="sample_bills")
    op.drop_constraint("uq_bill_client_external_id", "sample_bills", type_="unique")
    op.drop_column("sample_bills", "external_id")

    # Remove from sample_invoices
    op.drop_index("ix_invoice_external_id", table_name="sample_invoices")
    op.drop_constraint("uq_invoice_client_external_id", "sample_invoices", type_="unique")
    op.drop_column("sample_invoices", "external_id")

    # Remove from sample_vendors
    op.drop_index("ix_vendor_external_id", table_name="sample_vendors")
    op.drop_constraint("uq_vendor_client_external_id", "sample_vendors", type_="unique")
    op.drop_column("sample_vendors", "external_id")
