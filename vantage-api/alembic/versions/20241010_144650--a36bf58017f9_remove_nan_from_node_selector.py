"""remove nan from node selector

Revision ID: a36bf58017f9
Revises: 4f5b26ab7c5f
Create Date: 2024-10-10 14:46:50.00000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a36bf58017f9"
down_revision = "4f5b26ab7c5f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE aws_node_types
        SET gpu_manufacturer = NULL
        WHERE gpu_manufacturer = 'NaN';

        UPDATE aws_node_types
        SET gpu_name = NULL
        WHERE gpu_name = 'NaN';
    """
    )


def downgrade():
    op.execute(
        """
        UPDATE aws_node_types
        SET gpu_manufacturer = 'NaN'
        WHERE gpu_manufacturer IS NULL;

        UPDATE aws_node_types
        SET gpu_name = 'NaN'
        WHERE gpu_name IS NULL;
    """
    )
