"""Tests for the partitions GraphQL API."""
from collections.abc import Callable
from typing import AsyncGenerator

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Insert

from api.graphql_app import schema
from api.graphql_app.types import (
    ClusterRegion,
    Context,
)
from api.sql_app import models
from api.sql_app.enums import (
    CloudAccountEnum,
    ClusterProviderEnum,
    ClusterStatusEnum,
)


@pytest.mark.asyncio
async def test_create_partition__test_when_partition_is_duplicated(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when the cluster already has a partition with the same name."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    node_type = "t3.small"
    max_node_count = 10
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)

        query = insert(models.ClusterPartitionsModel).values(
            name=partition_name,
            node_type=node_type,
            max_node_count=max_node_count,
            is_default=True,
            cluster_name=cluster_name,
        )
        await session.execute(query)

        await session.commit()

    context = Context()

    query = """
        mutation addPartition($clusterName: String!, $name: String!) {
            createPartition(
                createPartitionInput: {
                    name: $name, clusterName: $clusterName, maxNodeCount: 10, nodeType: "t3.small"
                }
            ) {
                __typename
                ... on InvalidInput {
                    __typename
                    message
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}

    expected_message = f"The Cluster {cluster_name} already has a partition called {cluster_name}."

    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("createPartition").get("__typename") == "InvalidInput"
    assert response.data.get("createPartition").get("message") == expected_message


@pytest.mark.asyncio
async def test_create_partition__test_when_partition_is_created(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when a partition is created with success."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)
        await session.commit()

    context = Context()

    query = """
        mutation addPartition($clusterName: String!, $name: String!) {
            createPartition(
                createPartitionInput: {
                    name: $name,
                    clusterName: $clusterName,
                    maxNodeCount: 10,
                    nodeType: "t3.small"
                }
            ) {
                __typename
                ... on Partition {
                    id
                    name
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}

    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("createPartition").get("__typename") == "Partition"
    assert response.data.get("createPartition").get("name") == partition_name


@pytest.mark.asyncio
async def test_update_partition__test_when_partition_do_not_exist_in_the_cluster(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when the partition do not exist for the informed cluster."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)
        await session.commit()

    context = Context()

    query = """
        mutation updatePartition($clusterName: String!, $name: String!) {
            updatePartition(
                updatePartitionInput: {
                    partitionName: $name,
                    clusterName: $clusterName,
                    maxNodeCount: 1,
                    newPartitionName: "new_name",
                    nodeType: "t3.large"
                }
            ) {
                __typename
                ... on InvalidInput {
                   __typename
                   message
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}
    expected_message = f"Partition {partition_name} not found to the specified cluster {cluster_name}."
    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("updatePartition").get("__typename") == "InvalidInput"
    assert response.data.get("updatePartition").get("message") == expected_message


@pytest.mark.asyncio
async def test_update_partition__test_when_partition_is_updated(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when a partition is updated with success."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    node_type = "t3.small"
    max_node_count = 10
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)

        query = insert(models.ClusterPartitionsModel).values(
            name=partition_name,
            node_type=node_type,
            max_node_count=max_node_count,
            is_default=True,
            cluster_name=cluster_name,
        )
        await session.execute(query)
        await session.commit()

    context = Context()

    query = """
        mutation updatePartition($clusterName: String!, $name: String!) {
            updatePartition(
                updatePartitionInput: {
                    partitionName: $name,
                    clusterName: $clusterName,
                    maxNodeCount: 1,
                    newPartitionName: "new_name",
                    nodeType: "t3.large"
                }
            ) {
                __typename
                ... on Partition {
                   __typename
                   id
                   name
                   maxNodeCount
                   nodeType
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}
    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("updatePartition").get("__typename") == "Partition"
    assert response.data.get("updatePartition").get("name") == "new_name"
    assert response.data.get("updatePartition").get("maxNodeCount") == 1
    assert response.data.get("updatePartition").get("nodeType") == "t3.large"


@pytest.mark.asyncio
async def test_delete_partition__test_when_the_partition_do_not_exist_in_the_cluster(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when a partition do not exist in the informed cluster."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)

        await session.commit()

    context = Context()

    query = """
        mutation deletePartition($clusterName: String!, $name: String!) {
            deletePartition(
                partitionName: $name,
                clusterName: $clusterName,
            ) {
                __typename
                ... on InvalidInput {
                   __typename
                   message
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}
    response = await schema.execute(query, variable_values=variables, context_value=context)
    expected_message = f"Partition {partition_name} not found for the specified cluster {cluster_name}."
    assert response.errors is None
    assert response.data.get("deletePartition").get("__typename") == "InvalidInput"
    assert response.data.get("deletePartition").get("message") == expected_message


@pytest.mark.asyncio
async def test_delete_partition__test_when_the_partition_is_the_default_partition(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when a partition is the default and can't be deleted."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    node_type = "t2.small"
    max_node_count = 10
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)

        query = insert(models.ClusterPartitionsModel).values(
            name=partition_name,
            node_type=node_type,
            max_node_count=max_node_count,
            is_default=True,
            cluster_name=cluster_name,
        )
        await session.execute(query)

        await session.commit()

    context = Context()

    query = """
        mutation deletePartition($clusterName: String!, $name: String!) {
            deletePartition(
                partitionName: $name,
                clusterName: $clusterName,
            ) {
                __typename
                ... on InvalidInput {
                   __typename
                   message
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}
    response = await schema.execute(query, variable_values=variables, context_value=context)
    expected_message = f"Partition {partition_name} is a default partition and can't be deleted."
    assert response.errors is None
    assert response.data.get("deletePartition").get("__typename") == "InvalidInput"
    assert response.data.get("deletePartition").get("message") == expected_message


@pytest.mark.asyncio
async def test_delete_partition__test_when_the_partition_is_deleted(
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test when a partition is deleted with success."""
    cluster_name = "dummiest-cluster-name"
    partition_name = "compute"
    node_type = "t2.small"
    max_node_count = 10
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    async with get_session() as session:
        query = (
            insert(models.CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id=client_id,
            description="dummy description",
            owner_email=tester_email,
            creation_parameters={"region_name": region_name},
            provider=ClusterProviderEnum.aws,
            cloud_account_id=cloud_account_id,
        )
        await session.execute(query)

        query = insert(models.ClusterPartitionsModel).values(
            name=partition_name,
            node_type=node_type,
            max_node_count=max_node_count,
            is_default=False,
            cluster_name=cluster_name,
        )
        await session.execute(query)

        await session.commit()

    context = Context()

    query = """
        mutation deletePartition($clusterName: String!, $name: String!) {
            deletePartition(
                partitionName: $name,
                clusterName: $clusterName,
            ) {
                __typename
                ... on PartitionDeleted {
                   __typename
                   message
                }
            }
        }
    """

    variables = {"clusterName": cluster_name, "name": partition_name}
    response = await schema.execute(query, variable_values=variables, context_value=context)
    expected_message = "Partition has been deleted."
    assert response.errors is None
    assert response.data.get("deletePartition").get("__typename") == "PartitionDeleted"
    assert response.data.get("deletePartition").get("message") == expected_message
