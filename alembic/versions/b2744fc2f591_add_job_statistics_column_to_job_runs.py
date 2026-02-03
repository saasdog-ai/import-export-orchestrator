"""add job_statistics column to job_runs

Revision ID: b2744fc2f591
Revises: 004_add_external_id
Create Date: 2026-02-03 15:26:50.247819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2744fc2f591'
down_revision: Union[str, None] = '004_add_external_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('job_runs', sa.Column('job_statistics', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('job_runs', 'job_statistics')
