"""integrate storage with cloud accounts

Revision ID: 5d31f6787421
Revises: dd48e27efb1d
Create Date: 2024-02-12 12:36:45.205415

"""
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5d31f6787421"
down_revision = "dd48e27efb1d"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    op.add_column("storage", sa.Column("cloud_account_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_storage_cloud_account_id_cloud_account",
        "storage",
        "cloud_account",
        ["cloud_account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # fetch all storage columns and get the values of the column aws_arn
    result = conn.execute(sa.text("SELECT id, aws_arn FROM storage"))
    if result is None:
        storage_rows = []
    else:
        storage_rows = result.fetchall()

    # loop over the storage rows and create a record in the cloud_account table
    for idx, row in enumerate(storage_rows):
        query = sa.text(
            "INSERT INTO cloud_account (provider, name, assisted_cloud_account, description, attributes, created_at, updated_at) "
            "VALUES ('aws', :name, false, :desc, :attrs, now(), now()) RETURNING id"
        )
        cloud_account_id = conn.execute(
            query,
            name=f"CloudAccount{idx}",
            desc=f"Auto generated cloud account based on the role ARN set in storage whose ID is {row[0]}",
            attrs=json.dumps({"role_arn": row[1]}),
        ).fetchone()[0]

        # update the cloud_account_id column in the storage table
        conn.execute(
            sa.text("UPDATE storage SET cloud_account_id = :cloud_account_id WHERE id = :id"),
            cloud_account_id=cloud_account_id,
            id=row[0],
        )

    # drop the aws_arn column
    op.drop_column("storage", "aws_arn")


def downgrade():
    conn = op.get_bind()

    op.add_column("storage", sa.Column("aws_arn", sa.String(), nullable=True))

    # fetch the role_arn from the attributes column in the cloud_account table
    cloud_account_rows = conn.execute("SELECT id, attributes FROM cloud_account").fetchall()

    # loop over the cloud_account rows and update the aws_arn column in the storage table
    for row in cloud_account_rows:
        if row[1]:
            conn.execute(
                sa.text("UPDATE storage SET aws_arn = :aws_arn WHERE cloud_account_id = :cloud_account_id"),
                aws_arn=row[1]["role_arn"],
                cloud_account_id=row[0],
            )

    # drop the cloud_account_id column
    op.drop_column("storage", "cloud_account_id")
