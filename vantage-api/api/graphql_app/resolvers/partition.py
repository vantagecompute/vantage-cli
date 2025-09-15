"""Core module for defining GraphQL resolvers for partitions queries and mutations."""
from typing import Optional, Union

from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.sql.expression import Delete, Insert, Select, Update

from api.graphql_app.helpers import build_connection, get_partitions_and_node_info
from api.graphql_app.types import (
    ClusterOrderingInput,
    Connection,
    CreatePartitionInput,
    Info,
    InvalidInput,
    JSONScalar,
    Partition,
    PartitionDeleted,
    UpdatePartitionInput,
)
from api.sql_app import models
from api.sql_app.schemas import (
    PartitionRow,
)


async def get_cluster_partitions(
    info: Info,
    first: int = 20,
    after: int = 0,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[Partition]:
    """Get all clusters."""
    partitions_list = await build_connection(
        info=info,
        first=first,
        model=models.ClusterPartitionsModel,
        scalar_type=Partition,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.ClusterPartitionsModel.cluster],
    )
    async with info.context.db_session(info.context.token_data.organization) as sess:
        partitions = [edge.node for edge in partitions_list.edges]
        partitions = await get_partitions_and_node_info(partitions=partitions, sess=sess)
        for index in range(len(partitions_list.edges)):
            partitions_list.edges[index].node = partitions[index]

    return partitions_list


async def create_partition(
    info: Info, create_partition_input: CreatePartitionInput
) -> Union[InvalidInput, Partition]:
    """Update a partition for a defined cluster."""
    query: Select | Insert
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query: Select = select(models.ClusterPartitionsModel).where(
            and_(
                models.ClusterPartitionsModel.name == create_partition_input.name,
                models.ClusterPartitionsModel.cluster_name == create_partition_input.cluster_name,
            )
        )
        partition = (await sess.execute(query)).scalar_one_or_none()
        if partition is not None:
            return InvalidInput(
                message=(
                    f"The Cluster {create_partition_input.cluster_name} already "
                    f"has a partition called {create_partition_input.cluster_name}."
                )
            )

        payload = {
            "name": create_partition_input.name,
            "node_type": create_partition_input.node_type,
            "max_node_count": create_partition_input.max_node_count,
            "is_default": False,
            "cluster_name": create_partition_input.cluster_name,
        }

        query: Insert = (
            insert(models.ClusterPartitionsModel).values(**payload).returning(models.ClusterPartitionsModel)
        )
        new_partition = (await sess.execute(query)).one()
        await sess.commit()

    return Partition(**PartitionRow.from_orm(new_partition).dict())


async def update_partition(info: Info, update_partition_input: UpdatePartitionInput):
    """Update a partition for a defined cluster."""
    query: Select | Update
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query: Select = select(models.ClusterPartitionsModel).where(
            and_(
                models.ClusterPartitionsModel.name == update_partition_input.partition_name,
                models.ClusterPartitionsModel.cluster_name == update_partition_input.cluster_name,
            )
        )
        partition = (await sess.execute(query)).scalar_one_or_none()
        if partition is None:
            return InvalidInput(
                message=(
                    f"Partition {update_partition_input.partition_name} not found"
                    f" to the specified cluster {update_partition_input.cluster_name}."
                )
            )

        payload = {
            "name": update_partition_input.new_partition_name,
            "node_type": update_partition_input.node_type,
            "max_node_count": update_partition_input.max_node_count,
        }

        query: Update = (
            update(models.ClusterPartitionsModel)
            .where(
                and_(
                    models.ClusterPartitionsModel.name == update_partition_input.partition_name,
                    models.ClusterPartitionsModel.cluster_name == update_partition_input.cluster_name,
                )
            )
            .values(**payload)
            .returning(models.ClusterPartitionsModel)
        )
        updated_partition = (await sess.execute(query)).one()
        await sess.commit()

    return Partition(**PartitionRow.from_orm(updated_partition).dict())


async def delete_partition(info: Info, partition_name: str, cluster_name: str):
    """Update a partition of a defined cluster."""
    query: Select | Delete
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query: Select = select(models.ClusterPartitionsModel).where(
            and_(
                models.ClusterPartitionsModel.name == partition_name,
                models.ClusterPartitionsModel.cluster_name == cluster_name,
            )
        )
        partition_row = (await sess.execute(query)).scalar_one_or_none()
        if partition_row is None:
            return InvalidInput(
                message=(f"Partition {partition_name} not found for the specified cluster {cluster_name}.")
            )
        partition = Partition(**PartitionRow.from_orm(partition_row).dict())
        if partition.is_default:
            return InvalidInput(
                message=(f"Partition {partition_name} is a default partition and can't be deleted.")
            )

        query: Delete = delete(models.ClusterPartitionsModel).where(
            and_(
                models.ClusterPartitionsModel.name == partition_name,
                models.ClusterPartitionsModel.cluster_name == cluster_name,
            )
        )
        await sess.execute(query)
        await sess.commit()

    return PartitionDeleted()
