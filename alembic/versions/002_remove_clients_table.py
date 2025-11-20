"""Remove clients table and foreign key constraint

Revision ID: 002_remove_clients
Revises: 001_initial
Create Date: 2024-11-19 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_remove_clients'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraint from job_definitions
    op.drop_constraint('job_definitions_client_id_fkey', 'job_definitions', type_='foreignkey')
    
    # Drop clients table (clients are managed in the main SaaS app)
    op.drop_table('clients')


def downgrade() -> None:
    # Recreate clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Recreate foreign key constraint
    op.create_foreign_key(
        'job_definitions_client_id_fkey',
        'job_definitions',
        'clients',
        ['client_id'],
        ['id'],
        ondelete='CASCADE'
    )

