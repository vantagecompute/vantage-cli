"""add the notebook_servers table

Revision ID: d830f95409d7
Revises: f18198a1ab3c
Create Date: 2025-05-02 13:52:18.929644

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d830f95409d7"
down_revision = "f18198a1ab3c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notebook_servers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("owner", sa.String()),
        sa.Column("partition", sa.String(), nullable=True),
        sa.Column("server_url", sa.String(), nullable=True),
        sa.Column("cluster_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade():
    op.drop_table("notebook_servers")
