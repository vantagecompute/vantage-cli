"""patch cluster status enum

Revision ID: ab9dab55f0cc
Revises: 9a543dd78ead
Create Date: 2024-05-31 09:04:25.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "ab9dab55f0cc"
down_revision = "9a543dd78ead"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cluster",
        sa.Column(
            "creation_status_details", sa.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=True
        ),
    )
    op.execute(sa.text("ALTER TYPE clusterstatusenum RENAME VALUE 'connected' TO 'ready'"))
    op.execute(sa.text("ALTER TYPE clusterstatusenum RENAME VALUE 'prepared' TO 'preparing'"))
    op.execute(sa.text("ALTER TYPE clusterstatusenum ADD VALUE 'failed'"))


def downgrade():
    op.execute(sa.text("ALTER TYPE clusterstatusenum RENAME TO clusterstatusenum_old"))
    op.execute(sa.text("CREATE TYPE clusterstatusenum AS ENUM('prepared', 'connected', 'deleting')"))
    op.execute(
        sa.text(
            "ALTER TABLE cluster ALTER COLUMN status TYPE clusterstatusenum USING status::text::clusterstatusenum"
        )
    )
    op.execute(sa.text("DROP TYPE clusterstatusenum_old"))
    op.drop_column("cluster", "creation_status_details")
