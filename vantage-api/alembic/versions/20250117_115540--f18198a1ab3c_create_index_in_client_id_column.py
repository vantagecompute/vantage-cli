"""create index in `client_id` column in `cluster` table.

This index might help to improve the performance of the query that filters the clusters by the
`client_id` column. An indicative of the need for this index is the following trace on Sentry:
https://omnivector.sentry.io/performance/trace/c4854d7479cd4427a8e8f29a2cb0e01a

Issue reference: https://omnivector.sentry.io/issues/6092663810/events/1b6fb808843649fabf336061cee726f4/?project=4506588298608640

Revision ID: f18198a1ab3c
Revises: 0833941803e1
Create Date: 2025-01-16 11:55:40.00000

File created manually by Matheus Tosta <matheus@omnivector.solutions>

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "f18198a1ab3c"
down_revision = "0833941803e1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE INDEX idx_cluster_client_id
        ON cluster (client_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX idx_cluster_client_id;
        """
    )
