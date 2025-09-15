"""Create parition table
Revision ID: 4f5b26ab7c5f
Revises: 491abd909af0
Create Date: 2024-09-24 22:47:46.337678
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f5b26ab7c5f"
down_revision = "491abd909af0"
branch_labels = None
depends_on = None

metadata = sa.MetaData()

cluster_partitions_table = sa.Table(
    "cluster_partitions",
    metadata,
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("cluster_name", sa.String(), nullable=False),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("node_type", sa.String(), nullable=False),
    sa.Column("max_node_count", sa.Integer(), nullable=False),
    sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
    sa.ForeignKeyConstraint(
        ["cluster_name"],
        ["cluster.name"],
        ondelete="CASCADE",
    ),
    sa.PrimaryKeyConstraint("id"),
)


def upgrade():
    op.create_table(cluster_partitions_table.name, *cluster_partitions_table.columns)


def downgrade():
    op.drop_table("cluster_partitions")
