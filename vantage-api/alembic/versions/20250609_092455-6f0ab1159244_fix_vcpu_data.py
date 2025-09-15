"""fix the vcpu data in the `aws_node_types` table.

The vcpu data in the `aws_node_types` table was wrongly manipulated by the revision `491abd909af0`.
This migration corrects the data by using the `vCpus` column instead of the `vCpuCores` column.

Revision ID: 6f0ab1159244
Revises: f44f9f81f13d
Create Date: 2025-06-09 09:24:55.00000

File created manually by Matheus Tosta <matheus@omnivector.solutions>

"""
import pandas as pd  # noqa: I001
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6f0ab1159244"
down_revision = "f44f9f81f13d"
branch_labels = None
depends_on = None

metadata = sa.MetaData()

aws_node_types = sa.Table(
    "aws_node_types",
    metadata,
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("instance_type", sa.String(), nullable=False, index=True),
    sa.Column("aws_region", sa.String(), nullable=False, index=True),
    sa.Column("num_cpus", sa.Integer(), nullable=False),
)

aws_node_types_filters = sa.Table(
    "aws_node_types_filters",
    metadata,
    sa.Column("filter_name", sa.String(), primary_key=True, nullable=False),
    sa.Column("filter_values", postgresql.ARRAY(sa.String()), nullable=False),
)


def upgrade():  # noqa: D103
    df = pd.read_csv("alembic/data/aws-instances.csv")
    column_name_map = dict(
        instanceType="instance_type",
        location="aws_region",
        processorArchitectures="cpu_arch",
        vCpus="num_cpus",
        onDemandLinuxHr="price_per_hour",
    )
    pruned_df = df[column_name_map.keys()].rename(columns=column_name_map)
    pruned_df = pruned_df[pruned_df["cpu_arch"] == "x86_64"]
    pruned_df = pruned_df[pruned_df["price_per_hour"].notna()]  # 11024 elements with no duplicated rows

    # Update num_cpus for each unique (instance_type, aws_region) pair
    for _, row in pruned_df.iterrows():
        op.execute(
            aws_node_types.update()
            .where(
                aws_node_types.c.instance_type == row["instance_type"],
                aws_node_types.c.aws_region == row["aws_region"],
            )
            .values(num_cpus=int(row["num_cpus"]))
        )

    # Remove the num_cpus filter
    op.execute(aws_node_types_filters.delete().where(aws_node_types_filters.c.filter_name == "num_cpus"))

    # Add the new num_cpus filter values
    unique_num_cpus = list(map(str, sorted(pruned_df["num_cpus"].unique().tolist())))
    op.bulk_insert(
        aws_node_types_filters,
        [{"filter_name": "num_cpus", "filter_values": unique_num_cpus}],
    )


def downgrade():  # noqa: D103
    df = pd.read_csv("alembic/data/aws-instances.csv")
    column_name_map = dict(
        instanceType="instance_type",
        location="aws_region",
        processorArchitectures="cpu_arch",
        vCpuCores="num_cpus",
        onDemandLinuxHr="price_per_hour",
    )
    pruned_df = df[column_name_map.keys()].rename(columns=column_name_map)
    pruned_df = pruned_df[pruned_df["cpu_arch"] == "x86_64"]
    pruned_df = pruned_df[pruned_df["price_per_hour"].notna()]  # 11024 elements with no duplicated rows

    # Update num_cpus for each unique (instance_type, aws_region) pair
    for _, row in pruned_df.iterrows():
        op.execute(
            aws_node_types.update()
            .where(
                aws_node_types.c.instance_type == row["instance_type"],
                aws_node_types.c.aws_region == row["aws_region"],
            )
            .values(num_cpus=int(row["num_cpus"]))
        )

    # Remove the num_cpus filter
    op.execute(aws_node_types_filters.delete().where(aws_node_types_filters.c.filter_name == "num_cpus"))

    # Add the new num_cpus filter values
    unique_num_cpus = list(map(str, sorted(pruned_df["num_cpus"].unique().tolist())))
    op.execute(
        aws_node_types_filters.insert().values(
            [{"filter_name": "num_cpus", "filter_values": unique_num_cpus}]
        )
    )
