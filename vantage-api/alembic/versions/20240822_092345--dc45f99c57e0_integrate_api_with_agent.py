"""integrate API with Agent.

Revision ID: dc45f99c57e0
Revises: ab9dab55f0cc
Create Date: 2024-08-22 09:23:45.001340

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "dc45f99c57e0"
down_revision = "ab9dab55f0cc"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "slurm_cluster_config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
    )
    op.create_table(
        "all_partition_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
    )
    op.create_table(
        "all_node_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
    )
    op.create_table(
        "partition_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=False, index=True),
        sa.Column("name", sa.String, nullable=False, index=True),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
        sa.UniqueConstraint("cluster_name", "name"),
    )
    op.create_table(
        "node_info",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, unique=False, index=True),
        sa.Column("name", sa.String, nullable=False, index=True),
        sa.Column("partition_names", sa.ARRAY(sa.String), nullable=False),
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
        sa.UniqueConstraint("cluster_name", "name"),
    )
    op.create_table(
        "agent_health_check",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
        sa.Column("cluster_name", sa.String, nullable=False, index=True),
        sa.Column("interval", sa.Integer, nullable=False),
        sa.Column(
            "last_reported", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
        sa.UniqueConstraint("cluster_name"),
    )


def downgrade():
    op.drop_table("slurm_cluster_config")
    op.drop_table("all_partition_info")
    op.drop_table("all_node_info")
    op.drop_table("partition")
    op.drop_table("node")
    op.drop_table("agent_health_check")
