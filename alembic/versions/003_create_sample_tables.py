"""Create sample tables for import/export data

Revision ID: 003_create_sample_tables
Revises: 002_remove_clients_table
Create Date: 2026-01-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_sample_tables'
down_revision: Union[str, None] = '002_remove_clients'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sample_vendors table
    op.create_table(
        'sample_vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email_address', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('tax_number', sa.String(50), nullable=True),
        sa.Column('is_supplier', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_customer', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('address', postgresql.JSON(), nullable=True),
        sa.Column('phone_numbers', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index(op.f('ix_sample_vendors_client_id'), 'sample_vendors', ['client_id'], unique=False)

    # Create sample_projects table
    op.create_table(
        'sample_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(100), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('budget', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index(op.f('ix_sample_projects_client_id'), 'sample_projects', ['client_id'], unique=False)

    # Create sample_bills table (references sample_vendors and sample_projects)
    op.create_table(
        'sample_bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_number', sa.String(100), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('paid_on_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('line_items', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['vendor_id'], ['sample_vendors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['sample_projects.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_sample_bills_client_id'), 'sample_bills', ['client_id'], unique=False)

    # Create sample_invoices table (references sample_vendors)
    op.create_table(
        'sample_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_number', sa.String(100), nullable=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issue_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('paid_on_date', sa.DateTime(), nullable=True),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(10, 4), nullable=True),
        sa.Column('sub_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_tax_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('balance', sa.Numeric(15, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('line_items', postgresql.JSON(), nullable=True),
        sa.Column('tracking_categories', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['sample_vendors.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_sample_invoices_client_id'), 'sample_invoices', ['client_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sample_invoices_client_id'), table_name='sample_invoices')
    op.drop_table('sample_invoices')
    op.drop_index(op.f('ix_sample_bills_client_id'), table_name='sample_bills')
    op.drop_table('sample_bills')
    op.drop_index(op.f('ix_sample_projects_client_id'), table_name='sample_projects')
    op.drop_table('sample_projects')
    op.drop_index(op.f('ix_sample_vendors_client_id'), table_name='sample_vendors')
    op.drop_table('sample_vendors')
