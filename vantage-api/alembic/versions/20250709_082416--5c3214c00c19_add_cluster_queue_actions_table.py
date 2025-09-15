"""add cluster queue actions table.

Revision ID: 5c3214c00c19
Revises: 105df9d29f64
Create Date: 2025-07-09 08:24:16.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c3214c00c19"
down_revision = "105df9d29f64"
branch_labels = None
depends_on = None

metadata = sa.MetaData()


def upgrade():  # noqa: D103
    """Upgrade database schema."""
    cluster_queue_action_enum = sa.Enum("cancel", name="clusterqueueactionenum")
    op.create_table(
        "cluster_queue_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_name", sa.String(), nullable=False),
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column("action", cluster_queue_action_enum, nullable=False),
        sa.ForeignKeyConstraint(["cluster_name"], ["cluster.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["queue_info.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_name", "queue_id", name="uix_cluster_name_queue_id"),
    )
    op.create_index(
        op.f("ix_cluster_queue_actions_cluster_name"), "cluster_queue_actions", ["cluster_name"], unique=False
    )
    op.create_index(
        op.f("ix_cluster_queue_actions_queue_id"), "cluster_queue_actions", ["queue_id"], unique=False
    )


def downgrade():  # noqa: D103
    """Downgrade database schema."""
    op.drop_index(op.f("ix_cluster_queue_actions_queue_id"), table_name="cluster_queue_actions")
    op.drop_index(op.f("ix_cluster_queue_actions_cluster_name"), table_name="cluster_queue_actions")
    op.drop_table("cluster_queue_actions")
    sa.Enum(name="clusterqueueactionenum").drop(op.get_bind())
