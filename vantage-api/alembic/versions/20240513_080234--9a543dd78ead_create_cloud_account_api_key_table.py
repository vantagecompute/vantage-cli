"""create cloud account api key table

Revision ID: 9a543dd78ead
Revises: 6d0a7a4ce67e
Create Date: 2024-05-13 08:02:34.000000

"""
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a543dd78ead"
down_revision = "6d0a7a4ce67e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cloud_account_api_key",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_key", sa.String(), nullable=False, unique=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("cloud_account_api_key")
