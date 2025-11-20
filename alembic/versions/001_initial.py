"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create job_definitions table
    op.create_table(
        'job_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('job_type', sa.String(20), nullable=False),
        sa.Column('export_config', postgresql.JSON(), nullable=True),
        sa.Column('import_config', postgresql.JSON(), nullable=True),
        sa.Column('cron_schedule', sa.String(100), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_job_definitions_client_id'), 'job_definitions', ['client_id'], unique=False)

    # Create job_runs table
    op.create_table(
        'job_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['job_definitions.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_job_runs_job_id'), 'job_runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_runs_status'), 'job_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_job_runs_status'), table_name='job_runs')
    op.drop_index(op.f('ix_job_runs_job_id'), table_name='job_runs')
    op.drop_table('job_runs')
    op.drop_index(op.f('ix_job_definitions_client_id'), table_name='job_definitions')
    op.drop_table('job_definitions')
    op.drop_table('clients')

