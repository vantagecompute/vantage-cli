"""fix slow db query by indexing the cluster_name column in `cluster_partitions` table.

This migration also creates a foreign key constraint between the cluster_name column in the
`cluster_partitions` table and the name column in the `cluster` table. Despite the migration
`4f5b26ab7c5f` has a foreign key defined, it was not created in the database somehow.

Revision ID: 0833941803e1
Revises: a36bf58017f9
Create Date: 2025-01-13 10:39:40.00000

File created manually by Matheus Tosta <matheus@omnivector.solutions>

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0833941803e1"
down_revision = "a36bf58017f9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE INDEX idx_cluster_partitions_cluster_name
        ON cluster_partitions (cluster_name);
        """
    )
    op.create_foreign_key(
        "fk_cluster_partitions_cluster_name",
        "cluster_partitions",
        "cluster",
        ["cluster_name"],
        ["name"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("fk_cluster_partitions_cluster_name", "cluster_partitions")
    op.execute(
        """
        DROP INDEX idx_cluster_partitions_cluster_name;
        """
    )
