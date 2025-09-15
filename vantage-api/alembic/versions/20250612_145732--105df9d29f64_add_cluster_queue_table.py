"""add cluster queue table

Revision ID: 105df9d29f64
Revises: 6f0ab1159244
Create Date: 2025-06-12 14:57:32.916088

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "105df9d29f64"
down_revision = "6f0ab1159244"
branch_labels = None
depends_on = None

metadata = sa.MetaData()


def upgrade():  # noqa: D103
    op.create_table(
        "queue_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=False, index=True),
        sa.Column("name", sa.String, nullable=False, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE", onupdate="CASCADE"),
    )

    op.create_table(
        "all_queue_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
    )


def downgrade():  # noqa: D103
    op.drop_table("all_queue_info")
    op.drop_table("queue_info")
