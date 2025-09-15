"""map EC2 instance typer per region

Revision ID: 491abd909af0
Revises: dc45f99c57e0
Create Date: 2024-09-09 14:02:13.079537

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pandas as pd

# revision identifiers, used by Alembic.
revision = "491abd909af0"
down_revision = "dc45f99c57e0"
branch_labels = None
depends_on = None

metadata = sa.MetaData()


aws_node_types = sa.Table(
    "aws_node_types",
    metadata,
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("instance_type", sa.String(), nullable=False, index=True),
    sa.Column("aws_region", sa.String(), nullable=False, index=True),
    sa.Column("cpu_manufacturer", sa.String(), nullable=False, index=True),
    sa.Column("cpu_name", sa.String(), nullable=False, index=True),
    sa.Column("cpu_arch", sa.String(), nullable=False, index=True),
    sa.Column("num_cpus", sa.Integer(), nullable=False),
    sa.Column("memory", sa.Integer(), nullable=False),
    sa.Column("gpu_manufacturer", sa.String(), nullable=True, index=True),
    sa.Column("gpu_name", sa.String(), nullable=True, index=True),
    sa.Column("num_gpus", sa.Integer(), nullable=False),
    sa.Column("price_per_hour", sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("instance_type", "aws_region", name="uix_instance_type_aws_region"),
)
aws_node_types_filters = sa.Table(
    "aws_node_types_filters",
    metadata,
    sa.Column("filter_name", sa.String(), primary_key=True, nullable=False),
    sa.Column("filter_values", postgresql.ARRAY(sa.String()), nullable=False),
)


def upgrade():
    op.create_table(aws_node_types.name, *aws_node_types.columns)
    op.create_table(aws_node_types_filters.name, *aws_node_types_filters.columns)

    df = pd.read_csv("alembic/data/aws-instances.csv")
    column_name_map = dict(
        instanceType="instance_type",
        location="aws_region",
        processorManufacturer="cpu_manufacturer",
        processor="cpu_name",
        processorArchitectures="cpu_arch",
        vCpuCores="num_cpus",
        memorySizeInGiB="memory",
        gpuManufacturer="gpu_manufacturer",
        gpuName="gpu_name",
        gpuCount="num_gpus",
        onDemandLinuxHr="price_per_hour",
    )
    pruned_df = df[column_name_map.keys()].rename(columns=column_name_map)
    pruned_df = pruned_df[pruned_df["cpu_arch"] == "x86_64"]
    pruned_df = pruned_df[pruned_df["price_per_hour"].notna()]  # 11024 elements with no duplicated rows

    op.bulk_insert(aws_node_types, pruned_df.to_dict("records"))

    op.execute(aws_node_types_filters.delete())

    filter_dict = {}
    for col in pruned_df.columns:
        filter_dict[col] = pruned_df[col].unique().tolist()
    op.bulk_insert(
        aws_node_types_filters,
        [{"filter_name": k, "filter_values": v} for k, v in filter_dict.items()],
    )


def downgrade():
    op.drop_table("aws_node_types")
    op.drop_table("aws_node_types_filters")
