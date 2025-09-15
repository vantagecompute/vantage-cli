"""add the slurm_job_id column in the notebook_servers table.

Revision ID: f44f9f81f13d
Revises: d830f95409d7
Create Date: 2025-05-28 14:32:23.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "f44f9f81f13d"
down_revision = "d830f95409d7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notebook_servers", sa.Column("slurm_job_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("notebook_servers", "slurm_job_id")
