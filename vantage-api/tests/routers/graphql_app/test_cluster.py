"""Tests for the cluster GraphQL API."""
import base64
import itertools
import random
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from textwrap import dedent
from typing import AsyncContextManager, AsyncGenerator, Dict, List
from unittest import mock

import pytest
from botocore.exceptions import ClientError, ParamValidationError
from fastapi import status
from httpx import AsyncClient, Response
from mypy_boto3_cloudformation.type_defs import StackResourceTypeDef
from respx.router import MockRouter
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Delete, Insert, Select

from api.graphql_app import schema
from api.graphql_app.helpers import clean_cluster_name, cluster_name_to_client_id
from api.graphql_app.types import (
    AwsNodesFilters,
    AwsNodeTypes,
    Cluster,
    ClusterRegion,
    Connection,
    Context,
    Edge,
    PageInfo,
)
from api.identity.management_api import backend_client
from api.sql_app.enums import (
    CloudAccountEnum,
    ClusterProviderEnum,
    ClusterStatusEnum,
    SubscriptionTierClusters,
    SubscriptionTiersNames,
    SubscriptionTypesNames,
)
from api.sql_app.models import (
    AgentHealthCheckModel,
    AllNodeInfo,
    AllPartitionInfo,
    CloudAccountModel,
    ClusterModel,
    NodeModel,
    PartitionModel,
    SlurmClusterConfig,
    SubscriptionModel,
    SubscriptionTierModel,
    SubscriptionTypeModel,
)
from tests.conftest import SeededData


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_cluster_is_on_prem(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    seed_database: SeededData,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is on-prem."""
    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_resources = mock.Mock()

    cluster_name = seed_database.cluster_without_storage.name

    context = Context()

    query = """
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {"checkClusterAvailabilityForDeletion": {"isAvailable": True, "reason": None}}
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_cluster_is_not_found(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is not available for deletion."""
    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_resources = mock.Mock()

    context = Context()

    query = """
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterNotFound {
                    message
                }
            }
        }
    """

    variables = {"clusterName": "not-found"}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {"checkClusterAvailabilityForDeletion": {"message": "Cluster could not be found."}}
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_cluster_has_mount_points(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    seed_database: SeededData,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is not available for deletion.

    This test ensures that the query returns the correct response when the cluster has mount points.
    """
    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_resources = mock.Mock()
    mocked_cfn_ops.get_stack_status = mock.Mock()

    context = Context()

    query = """
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": seed_database.cluster.name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {
        "checkClusterAvailabilityForDeletion": {
            "isAvailable": False,
            "reason": "cluster_has_mount_points",
        }
    }
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_not_called()
    mocked_cfn_ops.get_stack_status.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_cluster_is_available(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is available for deletion."""
    cluster_name = "dummiest-cluster-name"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    vpc_id = "vpc-1234567890"
    query: str | Insert

    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_ec2_ops.list_instances_by_vpc_id.return_value = ["i-1234567890"]
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="CREATE_COMPLETE")
    mocked_cfn_ops.get_stack_resources = mock.Mock()
    mocked_cfn_ops.get_stack_resources.return_value = [
        StackResourceTypeDef(
            ResourceType="AWS::EC2::VPC",
            PhysicalResourceId=vpc_id,
            LogicalResourceId="VPC",
            Timestamp=datetime(2024, 5, 7),
            ResourceStatus="CREATE_COMPLETE",
        )
    ]

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(ClusterModel).values(
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
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {"checkClusterAvailabilityForDeletion": {"isAvailable": True, "reason": None}}
    mocked_ec2_ops.list_instances_by_vpc_id.assert_called_once_with(
        vpc_id=vpc_id, role_arn=role_arn, region_name=region_name
    )
    mocked_cfn_ops.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )
    mocked_cfn_ops.get_stack_status.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__get_stack_status_is_none(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when get_stack_status returns None."""
    cluster_name = "dummiest-cluster-name"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value=None)
    mocked_cfn_ops.get_stack_resources = mock.Mock()

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(ClusterModel).values(
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
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {"checkClusterAvailabilityForDeletion": {"isAvailable": True, "reason": None}}
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_not_called()
    mocked_cfn_ops.get_stack_status.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_stack_is_deleted(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the stack is deleted."""
    cluster_name = "dummiest-cluster-name"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="DELETE_COMPLETE")
    mocked_cfn_ops.get_stack_resources = mock.Mock(return_value=None)

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(ClusterModel).values(
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
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {"checkClusterAvailabilityForDeletion": {"isAvailable": True, "reason": None}}
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )
    mocked_cfn_ops.get_stack_status.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_cluster_has_compute_nodes(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is not available for deletion.

    This test ensures that the query returns the correct response when the cluster has compute nodes.
    """
    cluster_name = "dummiest-cluster-name"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    vpc_id = "vpc-1234567890"
    query: str | Insert

    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_ec2_ops.list_instances_by_vpc_id.return_value = ["i-1234567890", "i-2345678901", "i-3456789012"]
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="CREATE_COMPLETE")
    mocked_cfn_ops.get_stack_resources = mock.Mock()
    mocked_cfn_ops.get_stack_resources.return_value = [
        StackResourceTypeDef(
            ResourceType="AWS::EC2::VPC",
            PhysicalResourceId=vpc_id,
            LogicalResourceId="VPC",
            Timestamp=datetime(2024, 5, 7),
            ResourceStatus="CREATE_COMPLETE",
        )
    ]

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(ClusterModel).values(
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
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {
        "checkClusterAvailabilityForDeletion": {
            "isAvailable": False,
            "reason": "cluster_has_compute_nodes",
        }
    }
    mocked_ec2_ops.list_instances_by_vpc_id.assert_called_once_with(
        vpc_id=vpc_id, role_arn=role_arn, region_name=region_name
    )
    mocked_cfn_ops.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )
    mocked_cfn_ops.get_stack_status.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_graphql_check_cluster_availability_for_deletion__check_when_stack_is_buggy(
    mocked_ec2_ops: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    tester_email: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the checkClusterAvailabilityForDeletion query when the cluster is not available for deletion.

    This test ensures that the query returns the correct response when an unknown error has happened
    in the CloudFormation stack.
    """
    cluster_name = "dummiest-cluster-name"
    client_id = "dummy-client-id"
    cloud_account_name = "dummy-cloud-account-name"
    region_name = ClusterRegion.us_west_2.value
    role_arn = "arn:aws:iam::123456789012:role/role-name"
    query: str | Insert

    mocked_ec2_ops.list_instances_by_vpc_id = mock.Mock()
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="ROLLBACK_IN_PROGRESS")
    mocked_cfn_ops.get_stack_resources = mock.Mock()

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "name": cloud_account_name,
                    "provider": CloudAccountEnum.aws,
                    "description": "dummy description",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await session.execute(query)).scalar()

        query = insert(ClusterModel).values(
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
        query checkClusterAvailabilityForDeletion($clusterName: String!) {
            checkClusterAvailabilityForDeletion(clusterName: $clusterName) {
                ... on ClusterAvailableForDeletion {
                    isAvailable
                    reason
                }
            }
        }
    """

    variables = {"clusterName": cluster_name}

    resp = await schema.execute(query, variable_values=variables, context_value=context)

    assert resp.errors is None
    assert resp.data == {
        "checkClusterAvailabilityForDeletion": {
            "isAvailable": False,
            "reason": "unknown_error",
        }
    }
    mocked_ec2_ops.list_instances_by_vpc_id.assert_not_called()
    mocked_cfn_ops.get_stack_resources.assert_not_called()
    mocked_cfn_ops.get_stack_status.assert_called_once_with(
        stack_name=clean_cluster_name(cluster_name),
        cfn_config={"role_arn": role_arn, "region_name": region_name},
    )


@pytest.mark.asyncio
async def test_query_clusters__check_mask_attribute_error(
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
    enforce_strawberry_context_authentication: None,
):
    """Test the `clusters` query if an AttributeError is masked."""
    num_of_clusters_to_create = random.randint(1, 10)
    async with get_session() as sess:
        query = insert(ClusterModel).values(
            [
                {
                    "name": f"dummy{idx}",
                    "status": ClusterStatusEnum.ready,
                    "client_id": f"dummy{idx}",
                    "description": "dummy",
                    "owner_email": "foo@gmail.com",
                    "creation_parameters": {"dummy": "foo"},
                    "provider": ClusterProviderEnum.on_prem,
                    "cloud_account_id": None,
                }
                for idx in range(num_of_clusters_to_create)
            ]
        )
        await sess.execute(query)
        await sess.commit()

    context = Context()

    graphql_query = """
        query {
            clusters {
                total
                edges {
                    node {
                        cloudAccount {
                            name
                        }
                    }
                }
            }
        }
    """

    resp = await schema.execute(graphql_query, context_value=context)
    assert resp.errors is None
    assert resp.data == {
        "clusters": {
            "total": num_of_clusters_to_create,
            "edges": [{"node": {"cloudAccount": None}} for _ in range(num_of_clusters_to_create)],
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subscription_tier",
    list(SubscriptionTierClusters),
)
@mock.patch("api.graphql_app.resolvers.cluster.create_cluster", new_callable=mock.AsyncMock)
async def test_create_cluster__check_resource_limit_request__cloud_subscription_type(
    mocked_create_cluster: mock.AsyncMock,
    subscription_tier: SubscriptionTierClusters,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    sample_uuid: str,
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test the createCluster mutation when the user has reached the resource limit.

    It is expected that the resource creation is capped at the current subscription tier level.
    """
    query: Select | Insert | Delete
    async with get_session() as sess:
        query = select(SubscriptionTierModel.id).where(SubscriptionTierModel.name == subscription_tier.name)
        subscription_tier_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_tier_id is not None

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.cloud.value
        )
        subscription_type_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_type_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                organization_id=sample_uuid,
                tier_id=subscription_tier_id,
                type_id=subscription_type_id,
                detail_data={},
                is_free_trial=False,
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None

        num_of_clusters_to_create = (
            subscription_tier.value
            if subscription_tier != SubscriptionTierClusters.enterprise
            else SubscriptionTierClusters.pro.value + 1
        )

        query = insert(ClusterModel).values(
            [
                {
                    "name": f"dummy{idx}",
                    "status": ClusterStatusEnum.ready,
                    "client_id": f"dummy{idx}",
                    "description": "dummy",
                    "owner_email": "foo@gmail.com",
                    "creation_parameters": {"dummy": "foo"},
                    "provider": ClusterProviderEnum.on_prem,
                    "cloud_account_id": None,
                }
                for idx in range(num_of_clusters_to_create)
            ]
        )
        await sess.execute(query)
        await sess.commit()

    mocked_create_cluster.return_value = Cluster(
        name="testing resource limit",
        status=ClusterStatusEnum.ready,
        owner_email="foo@dummy.com",
        client_id="any",
        description=(
            "This cluster was created as a local demonstration cluster. It should "
            "be used for trying out Vantage features or testing things out."
        ),
        provider=ClusterProviderEnum.on_prem,
    )

    context = Context()

    graphql_query = """
        mutation createCluster {
            createCluster(createClusterInput: {
                name: "testing resource limit",
                description: "dummy"
                provider: on_prem
            }) {
                ... on Cluster {
                    name
                    status
                    description
                    clientId
                    provider
                }
            }
        }
    """

    resp = await schema.execute(graphql_query, context_value=context)
    if subscription_tier == SubscriptionTierClusters.enterprise:
        assert resp.errors is None
        mocked_create_cluster.assert_awaited_once()
    else:
        assert resp.errors is not None
        assert (
            resp.errors[0].message
            == "The resource creation is blocked because it requires a higher subscription tier."
        )
        mocked_create_cluster.assert_not_awaited()

    async with get_session() as sess:
        query = delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "num_of_clusters_to_create, max_num_of_clusters_allowed",
    list(
        itertools.product(
            [
                SubscriptionTierClusters.starter.value - 1,
                SubscriptionTierClusters.starter.value + 1,
                SubscriptionTierClusters.teams.value - 1,
                SubscriptionTierClusters.teams.value + 1,
                SubscriptionTierClusters.pro.value - 1,
                SubscriptionTierClusters.pro.value + 1,
            ],
            [SubscriptionTierClusters.pro.value],
        )
    ),
)
@mock.patch("api.graphql_app.resolvers.cluster.create_cluster", new_callable=mock.AsyncMock)
async def test_create_cluster__check_resource_limit_request__aws_subscription_type(
    mocked_create_cluster: mock.AsyncMock,
    num_of_clusters_to_create: int,
    max_num_of_clusters_allowed: int,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    sample_uuid: str,
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test the createCluster mutation when the user has reached the resource limit.

    It is expected that the AWS subscription type is capped at the pro level.
    """
    query: Select | Insert | Delete
    async with get_session() as sess:
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.teams.value
        )
        subscription_tier_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_tier_id is not None

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws.value
        )
        subscription_type_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_type_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                organization_id=sample_uuid,
                tier_id=subscription_tier_id,
                type_id=subscription_type_id,
                detail_data={},
                is_free_trial=False,
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None

        query = insert(ClusterModel).values(
            [
                {
                    "name": f"dummy{idx}",
                    "status": ClusterStatusEnum.ready,
                    "client_id": f"dummy{idx}",
                    "description": "dummy",
                    "owner_email": "foo@gmail.com",
                    "creation_parameters": {"dummy": "foo"},
                    "provider": ClusterProviderEnum.on_prem,
                    "cloud_account_id": None,
                }
                for idx in range(num_of_clusters_to_create)
            ]
        )
        await sess.execute(query)
        await sess.commit()

    mocked_create_cluster.return_value = Cluster(
        name="testing resource limit",
        status=ClusterStatusEnum.ready,
        owner_email="foo@dummy.com",
        client_id="any",
        description=(
            "This cluster was created as a local demonstration cluster. It should "
            "be used for trying out Vantage features or testing things out."
        ),
        provider=ClusterProviderEnum.on_prem,
    )

    context = Context()

    graphql_query = """
        mutation createCluster {
            createCluster(createClusterInput: {
                name: "testing resource limit",
                description: "dummy"
                provider: on_prem
            }) {
                ... on Cluster {
                    name
                    status
                    description
                    clientId
                    provider
                }
            }
        }
    """

    resp = await schema.execute(graphql_query, context_value=context)
    if num_of_clusters_to_create < max_num_of_clusters_allowed:
        assert resp.errors is None
        mocked_create_cluster.assert_awaited_once()
    else:
        assert resp.errors is not None
        assert (
            resp.errors[0].message
            == "The resource creation is blocked because it requires a higher subscription tier."
        )
        mocked_create_cluster.assert_not_awaited()

    async with get_session() as sess:
        query = delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.create_cluster")
async def test_graphql_create_demo_cluster__check_successful_creation(
    mocked_create_cluster: mock.AsyncMock, enforce_strawberry_context_authentication: None, tester_email
):
    """Test the createDemoCluster mutation when the cluster is successfully created."""
    mocked_create_cluster.return_value = Cluster(
        name="Demo Cluster",
        status=ClusterStatusEnum.preparing,
        owner_email=tester_email,
        client_id="any",
        description=(
            "This cluster was created as a local demonstration cluster. It should "
            "be used for trying out Vantage features or testing things out."
        ),
        provider=ClusterProviderEnum.on_prem,
    )

    context = Context()

    query = """
        mutation createDemoCluster {
            createDemoCluster {
                ... on Cluster {
                    name
                    clientId
                    description
                    status
                    provider
                }
            }
        }
    """

    resp = await schema.execute(query, context_value=context)

    assert resp.errors is None
    mocked_create_cluster.assert_awaited_once()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_when_no_secret_is_passed(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when the cluster is successfully created and no client secret is passed."""  # noqa: E501
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock()
    mocked_secrets.token_urlsafe.return_value = client_secret

    query: str | Select

    query = """\
    mutation createCluster(
        $input: CreateClusterInput!
    ) {
        createCluster(createClusterInput: $input) {
            ... on Cluster {
                name
                status
                clientId
                description
                provider
                ownerEmail
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": cluster_name,
                "description": description,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )

    cluster_data = response_data.get("data").get("createCluster")
    assert cluster_data.get("name") == cluster_name
    assert cluster_data.get("description") == description
    assert cluster_data.get("clientId") == client_id
    assert cluster_data.get("status") == "ready"
    assert cluster_data.get("provider") == "on_prem"

    query = select(ClusterModel).where(ClusterModel.name == cluster_name)
    async with get_session() as session:
        cluster: ClusterModel = (await session.execute(query)).scalar()

    assert cluster.name == cluster_name
    assert cluster.description == description
    assert cluster.client_id == client_id
    assert cluster.status == ClusterStatusEnum.ready
    assert cluster.provider == ClusterProviderEnum.on_prem

    mocked_secrets.token_urlsafe.assert_has_calls([mock.call(32), mock.call(32)])
    mocked_monitor_aws_cluster_status.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_when_secret_is_passed(
    mocked_monitor_aws_cluster_status: mock.Mock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when the cluster is successfully created and the client secret is passed."""  # noqa: E501
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock(return_value=client_secret)

    query = """\
    mutation createCluster(
        $input: CreateClusterInput!
    ) {
        createCluster(createClusterInput: $input) {
            ... on Cluster {
                name
                status
                clientId
                description
                provider
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": cluster_name,
                "description": description,
                "secret": client_secret,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )

    cluster = response_data.get("data").get("createCluster")
    assert cluster.get("name") == cluster_name
    assert cluster.get("description") == description
    assert cluster.get("clientId") == client_id
    assert cluster.get("status") == "ready"
    assert cluster.get("provider") == "on_prem"

    query = select(ClusterModel).where(ClusterModel.name == cluster_name)
    async with get_session() as session:
        cluster: ClusterModel = (await session.execute(query)).scalar()

    assert cluster.name == cluster_name
    assert cluster.description == description
    assert cluster.client_id == client_id
    assert cluster.status == ClusterStatusEnum.ready
    assert cluster.provider == ClusterProviderEnum.on_prem

    mocked_secrets.token_urlsafe.assert_called_once_with(32)
    mocked_monitor_aws_cluster_status.assert_not_called()


@pytest.mark.asyncio
async def test_graphql_create_cluster_with_existing_name(
    inject_security_header: Callable,
    test_client: AsyncClient,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when the cluster name is already in use."""
    inject_security_header("me", "compute:cluster:create")

    query: str | Select

    query = """\
    mutation createCluster($input: CreateClusterInput!) {
        createCluster(createClusterInput: $input) {
            ... on ClusterNameInUse {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": seed_database.cluster.name,
                "description": seed_database.cluster.description,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("data") == {"createCluster": {"message": "Cluster name is already in use"}}
    assert response_data.get("errors") is None

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 2


@pytest.mark.asyncio
async def test_graphql_update_cluster_record__check_when_passed_cluster_exists(
    inject_security_header: Callable,
    test_client: AsyncClient,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test update a cluster record mutation."""
    inject_security_header("me", "compute:cluster:update")

    cluster_description = "example"

    query = """
    mutation updateCluster(
        $input: UpdateClusterRecordInput!
    ) {
        updateCluster(updateClusterInput: $input) {
            ... on Cluster {
                name,
                status,
                clientId,
                description
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": seed_database.cluster.name,
                "description": cluster_description,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    cluster = response_data.get("data").get("updateCluster")

    assert cluster.get("name") == seed_database.cluster.name
    assert cluster.get("description") == cluster_description
    assert cluster.get("clientId") == seed_database.cluster.client_id
    assert cluster.get("status") == seed_database.cluster.status.name

    query = select(ClusterModel).where(ClusterModel.name == seed_database.cluster.name)
    async with get_session() as session:
        cluster: ClusterModel = (await session.execute(query)).scalar()

    assert cluster.name == seed_database.cluster.name
    assert cluster.description == cluster_description
    assert cluster.client_id == seed_database.cluster.client_id
    assert cluster.status == seed_database.cluster.status


@pytest.mark.asyncio
async def test_graphql_update_cluster_record__check_when_passed_cluster_doesnt_exist(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test update a cluster record mutation."""
    cluster_name = "example"
    cluster_description = "example"

    inject_security_header("me", "compute:cluster:update")

    query: str | Select

    query = """
    mutation updateCluster(
        $input: UpdateClusterRecordInput!
    ) {
        updateCluster(updateClusterInput: $input) {
            __typename
            ... on ClusterNotFound {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": cluster_name,
                "description": cluster_description,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("errors") is None
    assert response_data.get("data").get("updateCluster").get("__typename") == "ClusterNotFound"
    assert response_data.get("data").get("updateCluster").get("message") == "Cluster could not be found."

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 0


@pytest.mark.asyncio
async def test_graphql__delete_cluster_record__check_remaining_data_on_postgres(
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
):
    """Test the deleteCluster mutation when there's no error to delete the cluster record."""
    client_uuid = str(uuid.uuid4())
    service_account_id = "dummy-service-account-id"

    respx_mock.get(
        "/admin/realms/vantage/clients", params={"clientId": seed_database.cluster_without_storage.client_id}
    ).mock(
        return_value=Response(
            200, json=[{"id": client_uuid, "clientId": seed_database.cluster_without_storage.client_id}]
        )
    )
    respx_mock.get(f"/admin/realms/vantage/clients/{client_uuid}/service-account-user").mock(
        return_value=Response(200, json={"id": service_account_id})
    )
    respx_mock.delete(f"/admin/realms/vantage/organizations/{organization_id}/members/{service_account_id}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/clients/{client_uuid}").mock(return_value=Response(204))

    query: str | Select

    query = """
    mutation deleteCloudCluster($clusterName: String!) {
        deleteCluster(clusterName: $clusterName) {
            __typename
            ... on ClusterDeleted {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {"clusterName": seed_database.cluster_without_storage.name},
    }

    inject_security_header("me", "compute:cluster:delete")
    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("data").get("deleteCluster").get("__typename") == "ClusterDeleted"
    assert response_data.get("data").get("deleteCluster").get("message") == "Cluster has been deleted."

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 1


@pytest.mark.asyncio
async def test_graphql__delete_cluster_record__check_when_theres_error_to_delete_client(
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    create_dummy_subscription: None,
):
    """Test the deleteCluster mutation when there's error to delete the client."""
    client_uuid = str(uuid.uuid4())
    service_account_id = "dummy-service-account-id"

    respx_mock.get(
        "/admin/realms/vantage/clients", params={"clientId": seed_database.cluster_without_storage.client_id}
    ).mock(
        return_value=Response(
            200, json=[{"id": client_uuid, "clientId": seed_database.cluster_without_storage.client_id}]
        )
    )
    respx_mock.get(f"/admin/realms/vantage/clients/{client_uuid}/service-account-user").mock(
        return_value=Response(200, json={"id": service_account_id})
    )
    respx_mock.delete(f"/admin/realms/vantage/organizations/{organization_id}/members/{service_account_id}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/clients/{client_uuid}").mock(return_value=Response(500))

    query = """
    mutation deleteCloudCluster($clusterName: String!) {
        deleteCluster(clusterName: $clusterName) {
            __typename
            ... on UnexpectedBehavior {
                message
            }
        }
    }
    """

    body = {
        "query": dedent(query),
        "variables": {"clusterName": seed_database.cluster_without_storage.name},
    }

    inject_security_header("me", "compute:cluster:delete")
    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("data").get("deleteCluster").get("__typename") == "UnexpectedBehavior"
    assert (
        response_data.get("data").get("deleteCluster").get("message")
        == "Couldn't delete client, contact support for details"
    )

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 2


@pytest.mark.asyncio
async def test_graphql__delete_cluster_record__check_when_theres_no_error_to_fetch_default_client_but_client_is_not_fetched_indeed(  # noqa
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test the deleteCluster mutation when there's no error to fetch the default client but the client is not fetched indeed."""  # noqa: E501
    respx_mock.get(
        "/admin/realms/vantage/clients", params={"clientId": seed_database.cluster_without_storage.client_id}
    ).mock(return_value=Response(200, json=[]))

    query: str | Select

    query = """
    mutation deleteCloudCluster($clusterName: String!) {
        deleteCluster(clusterName: $clusterName) {
            __typename
            ... on UnexpectedBehavior {
                message
            }
        }
    }
    """

    body = {
        "query": dedent(query),
        "variables": {"clusterName": seed_database.cluster_without_storage.name},
    }

    inject_security_header("me", "compute:cluster:delete")
    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("data").get("deleteCluster").get("__typename") == "UnexpectedBehavior"
    assert (
        response_data.get("data").get("deleteCluster").get("message")
        == "Unexpected behaviour in which the cluster record exists but the client doesn't. Contact support"
    )

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 2


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_when_no_inputs_are_provided_for_aws_cluster(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when no inputs are provided for AWS cluster."""
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock()
    mocked_secrets.token_urlsafe.return_value = client_secret

    query: str | Select

    query = """\
    mutation createCluster($name: String!, $description: String!) {
        createCluster(createClusterInput: {
            name: $name
            description: $description
            provider: aws
    }) {
            ... on InvalidInput {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {"name": cluster_name, "description": description},
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("createCluster") == {
        "message": "Either provider_attributes and partitions shall be informed for aws cluster type."
    }

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 0
    mocked_monitor_aws_cluster_status.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_when_is_not_possible_to_apply_template(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    cfn_mock: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when there's error to apply the CloudFormation template."""
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock(return_value=client_secret)

    respx_mock.delete(f"/admin/realms/vantage/clients/{client_uuid}").mock(return_value=Response(204))

    query: str | Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel.id)
        cloud_account_id = (await session.execute(query)).scalar()
        await session.commit()

    query = """\
    mutation createCluster(
        $cloudAccountId: Int!
        $clusterName: String!
        $clusterDescription: String!
        $awsSshKeyPair: String!
    ) {
    createCluster(createClusterInput: {
        name: $clusterName
        description: $clusterDescription
        provider: aws
        providerAttributes: {
            aws: {
                headNodeInstanceType: "c4.2xlarge"
                cloudAccountId: $cloudAccountId
                regionName: us_west_2
                keyPair: $awsSshKeyPair
            }
        }
        partitions: [
            {
                name: "compute",
                nodeType: "m4.4xlarge",
                maxNodeCount: 10,
                isDefault: true
            }
        ]
    }) {
            __typename
            ... on ClusterCouldNotBeDeployed {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "cloudAccountId": cloud_account_id,
            "clusterName": cluster_name,
            "clusterDescription": description,
            "awsSshKeyPair": "foo",
        },
    }

    cfn_mock.apply_template = mock.Mock()
    cfn_mock.apply_template.side_effect = Exception("Test error: not possible to apply template")

    response = await test_client.post("/cluster/graphql", json=body)
    response_json = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_json.get("data").get("createCluster").get("__typename") == "ClusterCouldNotBeDeployed"
    assert (
        response_json.get("data").get("createCluster").get("message")
        == "Cluster could not be deployed on AWS"
    )
    assert response_json.get("errors") is None
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )
    cfn_mock.apply_template.assert_called_once_with(
        config={
            "role_arn": "arn:aws:iam::123456789012:role/role-name",
            "region_name": ClusterRegion.us_west_2.value,
        },
        slurm_cluster_name=clean_cluster_name(cluster_name),
        api_cluster_name=cluster_name,
        head_node_instance_type="c4.2xlarge",
        key_pair="foo",
        networking=None,
        client_id=client_id,
        client_secret=client_secret,
        jupyterhub_token=client_secret,
        cloud_account_id=cloud_account_id,
        region_name=ClusterRegion.us_west_2.value,
        partitions=[{"name": "compute", "node_type": "m4.4xlarge", "max_node_count": 10, "is_default": True}],
    )
    mocked_monitor_aws_cluster_status.assert_not_called()

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 0


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__supply_networking__check_when_is_not_possible_to_apply_template(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    cfn_mock: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    create_dummy_subscription: None,
):
    """Test the createCluster mutation when there's error to apply the CloudFormation template."""
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"
    vpc_id = "vpc-123345basfd"
    subnet_id = "subnet-abc391jf"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock(return_value=client_secret)

    respx_mock.delete(f"/admin/realms/vantage/clients/{client_uuid}").mock(return_value=Response(204))

    query: str | Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel.id)
        cloud_account_id = (await session.execute(query)).scalar()
        await session.commit()

    query = """\
    mutation createCluster(
        $cloudAccountId: Int!
        $clusterName: String!
        $clusterDescription: String!
        $awsSshKeyPair: String!
        $vpcId: String!
        $headNodeSubnetId: String!
    ) {
    createCluster(createClusterInput: {
        name: $clusterName
        description: $clusterDescription
        provider: aws
        providerAttributes: {
            aws: {
                headNodeInstanceType: "c4.2xlarge"
                cloudAccountId: $cloudAccountId
                regionName: us_west_2
                keyPair: $awsSshKeyPair
                networking: {
                    vpcId: $vpcId
                    headNodeSubnetId: $headNodeSubnetId
                }
            }
        }
        partitions: [{
            name: "compute"
            nodeType: "t3.small"
            maxNodeCount: 10
            isDefault: true
        }]
    }) {
            __typename
            ... on ClusterCouldNotBeDeployed {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "cloudAccountId": cloud_account_id,
            "clusterName": cluster_name,
            "clusterDescription": description,
            "awsSshKeyPair": "foo",
            "vpcId": vpc_id,
            "headNodeSubnetId": subnet_id,
        },
    }

    def _raise_test_error(**kwargs):
        raise Exception("Test error: not possible to apply template")

    cfn_mock.apply_template = mock.Mock()
    cfn_mock.apply_template.side_effect = _raise_test_error

    response = await test_client.post("/cluster/graphql", json=body)
    response_json = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_json.get("data").get("createCluster").get("__typename") == "ClusterCouldNotBeDeployed"
    assert (
        response_json.get("data").get("createCluster").get("message")
        == "Cluster could not be deployed on AWS"
    )
    assert response_json.get("errors") is None
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )
    cfn_mock.apply_template.assert_called_once_with(
        config={
            "role_arn": "arn:aws:iam::123456789012:role/role-name",
            "region_name": ClusterRegion.us_west_2.value,
        },
        slurm_cluster_name=clean_cluster_name(cluster_name),
        api_cluster_name=cluster_name,
        head_node_instance_type="c4.2xlarge",
        key_pair="foo",
        networking={
            "vpc_id": vpc_id,
            "head_node_subnet_id": subnet_id,
            "compute_node_subnet_id": None,
        },
        client_id=client_id,
        client_secret=client_secret,
        jupyterhub_token=client_secret,
        cloud_account_id=cloud_account_id,
        region_name=ClusterRegion.us_west_2.value,
        partitions=[{"name": "compute", "node_type": "t3.small", "max_node_count": 10, "is_default": True}],
    )
    mocked_monitor_aws_cluster_status.assert_not_called()

    query = select(func.count()).select_from(ClusterModel)
    async with get_session() as session:
        number_of_clusters: int = (await session.execute(query)).scalar()

    assert number_of_clusters == 0


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_when_template_is_applied(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    cfn_mock: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    tester_email: str,
    create_dummy_subscription: None,
):
    """Test whether the mutation creates a cluster record and applies the template on AWS."""
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock()
    mocked_secrets.token_urlsafe.return_value = client_secret

    query: str | Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel.id)
        cloud_account_id = (await session.execute(query)).scalar()
        await session.commit()

    query = """\
    mutation createCluster(
        $cloudAccountId: Int!
        $clusterName: String!
        $clusterDescription: String!
        $awsSshKeyPair: String!
    ) {
    createCluster(createClusterInput: {
        name: $clusterName
        description: $clusterDescription
        provider: aws
        providerAttributes: {
            aws: {
                headNodeInstanceType: "c4.2xlarge"
                cloudAccountId: $cloudAccountId
                regionName: us_west_2
                keyPair: $awsSshKeyPair
            }
        }
        partitions: [{
            name: "compute"
            nodeType: "t3.small"
            maxNodeCount: 10
            isDefault: true
        }]
    }) {
            __typename
            ... on Cluster {
                name
                status
                clientId
                cloudAccountId
                ownerEmail
                provider
                creationParameters
                description
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "cloudAccountId": cloud_account_id,
            "clusterName": cluster_name,
            "clusterDescription": description,
            "awsSshKeyPair": "foo",
        },
    }

    cfn_mock.apply_template = mock.Mock()

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()
    assert response_data.get("errors") is None
    payload = response_data.get("data").get("createCluster")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert payload.get("__typename") == "Cluster"
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )
    cfn_mock.apply_template.assert_called_once_with(
        config={
            "role_arn": "arn:aws:iam::123456789012:role/role-name",
            "region_name": ClusterRegion.us_west_2.value,
        },
        slurm_cluster_name=clean_cluster_name(cluster_name),
        api_cluster_name=cluster_name,
        head_node_instance_type="c4.2xlarge",
        key_pair="foo",
        networking=None,
        client_id=client_id,
        client_secret=client_secret,
        jupyterhub_token=client_secret,
        cloud_account_id=cloud_account_id,
        region_name=ClusterRegion.us_west_2.value,
        partitions=[
            {
                "name": "compute",
                "node_type": "t3.small",
                "max_node_count": 10,
                "is_default": True,
            }
        ],
    )
    mocked_monitor_aws_cluster_status.assert_called_once_with(
        organization_id,
        "us-west-2",
        "arn:aws:iam::123456789012:role/role-name",
        clean_cluster_name(cluster_name),
        cluster_name,
    )

    query = select(ClusterModel).where(ClusterModel.name == cluster_name)
    async with get_session() as session:
        cluster: ClusterModel = (await session.execute(query)).scalar()

    assert cluster.name == cluster_name == payload.get("name")
    assert cluster.description == description == payload.get("description")
    assert cluster.client_id == client_id == payload.get("clientId")
    assert cluster.cloud_account_id == cloud_account_id == payload.get("cloudAccountId")
    assert cluster.owner_email == tester_email
    assert cluster.provider == CloudAccountEnum.aws
    assert cluster.creation_parameters == {
        "cloud_account_id": cloud_account_id,
        "head_node_instance_type": "c4.2xlarge",
        "jupyterhub_token": client_secret,
        "key_pair": "foo",
        "networking": None,
        "region_name": ClusterRegion.us_west_2.value,
    }


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__supply_networking__check_when_template_is_applied(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    cfn_mock: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
    tester_email: str,
    create_dummy_subscription: None,
):
    """Test whether the mutation creates a cluster record and applies the template on AWS."""
    inject_security_header("me", "compute:cluster:create")

    cluster_name = "OSLCluster"
    client_id = cluster_name_to_client_id(cluster_name, organization_id)
    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"
    vpc_id = "vpc-123345basfd"
    subnet_id = "subnet-abc391jf"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock()
    mocked_secrets.token_urlsafe.return_value = client_secret

    query: str | Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel.id)
        cloud_account_id = (await session.execute(query)).scalar()
        await session.commit()

    query = """\
    mutation createCluster(
        $cloudAccountId: Int!
        $clusterName: String!
        $clusterDescription: String!
        $awsSshKeyPair: String!
        $vpcId: String!
        $headNodeSubnetId: String!
    ) {
    createCluster(createClusterInput: {
        name: $clusterName
        description: $clusterDescription
        provider: aws
        providerAttributes: {
            aws: {
                headNodeInstanceType: "c4.2xlarge"
                cloudAccountId: $cloudAccountId
                regionName: us_west_2
                keyPair: $awsSshKeyPair
                networking: {
                    vpcId: $vpcId
                    headNodeSubnetId: $headNodeSubnetId
                }
            }
        }
        partitions: [{
            name: "compute"
            nodeType: "t3.small"
            maxNodeCount: 10
            isDefault: true
        }]
    }) {
            __typename
            ... on Cluster {
                name
                status
                clientId
                cloudAccountId
                ownerEmail
                provider
                creationParameters
                description
            }
            ... on InvalidInput {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "cloudAccountId": cloud_account_id,
            "clusterName": cluster_name,
            "clusterDescription": description,
            "awsSshKeyPair": "foo",
            "vpcId": vpc_id,
            "headNodeSubnetId": subnet_id,
        },
    }

    cfn_mock.apply_template = mock.Mock()

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()
    payload = response_data.get("data").get("createCluster")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert payload.get("__typename") == "Cluster"
    mocked_set_up_cluster_config_on_keycloak.assert_called_once_with(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_id,
        client_description=f"Client for authentication purposes of cluster {cluster_name} - Org ID: {organization_id}",  # noqa: E501
        client_secret=client_secret,
        organization_id=organization_id,
    )
    cfn_mock.apply_template.assert_called_once_with(
        config={
            "role_arn": "arn:aws:iam::123456789012:role/role-name",
            "region_name": ClusterRegion.us_west_2.value,
        },
        slurm_cluster_name=clean_cluster_name(cluster_name),
        api_cluster_name=cluster_name,
        head_node_instance_type="c4.2xlarge",
        key_pair="foo",
        networking={
            "vpc_id": vpc_id,
            "head_node_subnet_id": subnet_id,
            "compute_node_subnet_id": None,
        },
        client_id=client_id,
        client_secret=client_secret,
        jupyterhub_token=client_secret,
        cloud_account_id=cloud_account_id,
        region_name=ClusterRegion.us_west_2.value,
        partitions=[
            {
                "name": "compute",
                "node_type": "t3.small",
                "max_node_count": 10,
                "is_default": True,
            }
        ],
    )
    mocked_monitor_aws_cluster_status.assert_called_once_with(
        organization_id,
        "us-west-2",
        "arn:aws:iam::123456789012:role/role-name",
        clean_cluster_name(cluster_name),
        cluster_name,
    )

    query = select(ClusterModel).where(ClusterModel.name == cluster_name)
    async with get_session() as session:
        cluster: ClusterModel = (await session.execute(query)).scalar()

    assert cluster.name == cluster_name == payload.get("name")
    assert cluster.description == description == payload.get("description")
    assert cluster.client_id == client_id == payload.get("clientId")
    assert cluster.cloud_account_id == cloud_account_id == payload.get("cloudAccountId")
    assert cluster.owner_email == tester_email
    assert cluster.provider == CloudAccountEnum.aws
    assert cluster.creation_parameters == {
        "cloud_account_id": cloud_account_id,
        "head_node_instance_type": "c4.2xlarge",
        "jupyterhub_token": client_secret,
        "key_pair": "foo",
        "networking": {
            "compute_node_subnet_id": None,
            "head_node_subnet_id": subnet_id,
            "vpc_id": vpc_id,
        },
        "region_name": ClusterRegion.us_west_2.value,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cluster_name",
    [
        "invalid string",  # Contains a space
        "another_invalid",  # Contains an underscore
        "with-hyphen-",  # Ends with a hyphen
        "has.a.dot",  # Contains a dot
        "question?",  # Contains a question mark
        "space-at-the-end ",  # Contains a space at the end
        "spaced string",  # Spaced string
        "exclamation!",  # Contains an exclamation mark
        "at@symbol",  # Contains an at symbol
        "plus+sign",  # Contains a plus sign
        "equals=sign",  # Contains an equals sign
        "123+",  # Ends with a non-alphanumeric character
        "-",  # Only a hyphen
        "",  # Empty string
        " ",  # Only a space
        "  ",  # Multiple spaces
        "\t",  # Tab character
        "\n",  # Newline character
        "a" * 129,  # 129 characters long
        "b" * 150,  # 150 characters long
        "c" * 200,  # 200 characters long
        (
            "This string is way too long and exceeds the 128 "
            "character limit by a significant margin."  # Too long
        ),
    ],
)
@mock.patch("api.graphql_app.resolvers.cluster.uuid")
@mock.patch("api.graphql_app.resolvers.cluster.secrets")
@mock.patch("api.graphql_app.resolvers.cluster.cfn_ops")
@mock.patch("api.graphql_app.resolvers.cluster.set_up_cluster_config_on_keycloak")
@mock.patch("api.graphql_app.resolvers.cluster.monitor_aws_cluster_status")
async def test_graphql_create_cluster_record__check_cluster_name_regex(
    mocked_monitor_aws_cluster_status: mock.MagicMock,
    mocked_set_up_cluster_config_on_keycloak: mock.Mock,
    cfn_mock: mock.MagicMock,
    mocked_secrets: mock.Mock,
    mocked_uuid: mock.Mock,
    cluster_name: str,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    tester_email: str,
    create_dummy_subscription: None,
):
    """Test the cluster creation rejection if the cluster name does not match a regex.

    The conditions for the cluster name are:
        1. It can contain upper and lower case letters, numbers and hyphens.
        2. It cannot end with a hyphen.
        3. It can have at most 128 characters.
    """
    inject_security_header("me", "compute:cluster:create")

    description = "dummy description"
    client_uuid = str(uuid.uuid4())
    client_secret = "dummy-secret"
    vpc_id = "vpc-123345basfd"
    subnet_id = "subnet-abc391jf"

    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = client_uuid

    mocked_secrets.token_urlsafe = mock.Mock()
    mocked_secrets.token_urlsafe.return_value = client_secret

    query: str | Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel.id)
        cloud_account_id = (await session.execute(query)).scalar()
        await session.commit()

    query = """\
    mutation createCluster(
        $cloudAccountId: Int!
        $clusterName: String!
        $clusterDescription: String!
        $awsSshKeyPair: String!
        $vpcId: String!
        $headNodeSubnetId: String!
    ) {
    createCluster(createClusterInput: {
        name: $clusterName
        description: $clusterDescription
        provider: aws
        providerAttributes: {
            aws: {
                headNodeInstanceType: "c4.2xlarge"
                cloudAccountId: $cloudAccountId
                regionName: us_west_2
                keyPair: $awsSshKeyPair
                networking: {
                    vpcId: $vpcId
                    headNodeSubnetId: $headNodeSubnetId
                }
            }
        }
        partitions: [{
            name: "compute"
            nodeType: "t3.small"
            maxNodeCount: 10
            isDefault: true
        }]
    }) {
            __typename
            ... on Cluster {
                name
                status
                clientId
                cloudAccountId
                ownerEmail
                provider
                creationParameters
                description
            }
            ... on InvalidInput {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "cloudAccountId": cloud_account_id,
            "clusterName": cluster_name,
            "clusterDescription": description,
            "awsSshKeyPair": "foo",
            "vpcId": vpc_id,
            "headNodeSubnetId": subnet_id,
        },
    }

    cfn_mock.apply_template = mock.Mock()

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()
    payload = response_data.get("data").get("createCluster")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert payload.get("__typename") == "InvalidInput"
    assert (
        payload.get("message")
        == "Cluster name must contain only alphanumeric characters and hyphens with no spaces"
    )
    mocked_set_up_cluster_config_on_keycloak.assert_not_called()
    cfn_mock.apply_template.assert_not_called()
    mocked_monitor_aws_cluster_status.assert_not_called()
    mocked_uuid.uuid4.assert_not_called()
    mocked_secrets.token_urlsafe.assert_not_called()

    query = select(ClusterModel).where(ClusterModel.name == cluster_name)
    async with get_session() as session:
        cluster: ClusterModel | None = (await session.execute(query)).scalar_one_or_none()

    assert cluster is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ssh_key_list",
    [
        ([{"KeyName": "foo"}, {"KeyName": "bar"}, {"KeyName": "baz"}]),
        ([{"KeyName": "foo"}]),
        ([]),
    ],
)
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_ssh_keys__check_no_error(
    mocked_ec2_ops: mock.Mock,
    ssh_key_list: List[str],
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the query returns no error when the user has the required permissions."""
    mocked_ec2_ops.get_ssh_key_pairs = mock.Mock()
    mocked_ec2_ops.get_ssh_key_pairs.return_value = ssh_key_list

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    inject_security_header("me", "compute:ssh-keys:read")

    graphql_query = """
    query sshKeys($cloudAccountId: Int!, $region: ClusterRegion!) {
        sshKeys(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on AwsSshKeys {
                keyPairNames
            }
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("sshKeys").get("__typename") == "AwsSshKeys"
    assert response_data.get("data").get("sshKeys").get("keyPairNames") == [
        key.get("KeyName") for key in ssh_key_list
    ]

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_ssh_keys__check_param_validation_error(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the query returns an error when there's a validation error."""
    mocked_ec2_ops.get_ssh_key_pairs = mock.Mock()
    mocked_ec2_ops.get_ssh_key_pairs.side_effect = ParamValidationError(report="Dummy error message")

    inject_security_header("me", "compute:ssh-keys:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query sshKeys($cloudAccountId: Int!, $region: ClusterRegion!) {
        sshKeys(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on ParameterValidationError {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("sshKeys").get("__typename") == "ParameterValidationError"
    assert (
        response_data.get("data").get("sshKeys").get("message")
        == "Parameter validation failed:\nDummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_ssh_keys__check_unauthorized_operation(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_ssh_key_pairs = mock.Mock()
    mocked_ec2_ops.get_ssh_key_pairs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "UnauthorizedOperation",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_key_pairs",
    )

    inject_security_header("me", "compute:ssh-keys:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query sshKeys($cloudAccountId: Int!, $region: ClusterRegion!) {
        sshKeys(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("sshKeys").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("sshKeys").get("message") == (
        "An error occurred (UnauthorizedOperation) when calling"
        " the describe_key_pairs operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_ssh_keys__check_access_denied(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_ssh_key_pairs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_key_pairs",
    )

    inject_security_header("me", "compute:ssh-keys:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query sshKeys($cloudAccountId: Int!, $region: ClusterRegion!) {
        sshKeys(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("sshKeys").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("sshKeys").get("message") == (
        "An error occurred (AccessDenied) when calling the describe_key_pairs operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
async def test_query_ssh_keys__cloud_account_not_found(
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test whether the query returns the type InvalidInput when the cloud account doesn't exist."""
    inject_security_header("me", "compute:ssh-keys:read")

    graphql_query = """
    query sshKeys($cloudAccountId: Int!, $region: ClusterRegion!) {
        sshKeys(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {"query": graphql_query, "variables": {"cloudAccountId": 100, "region": "us_west_2"}}

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("sshKeys").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("sshKeys").get("message") == "Cloud account not found"


class TestQueryEnabledAwsRegions:
    """Test the query enabledAwsRegions."""

    @pytest.mark.asyncio
    async def test_query_enabled_aws_regions__cloud_account_not_found(
        self, enforce_strawberry_context_authentication: None
    ):
        """Test the query enabledAwsRegions when the inputed cloud account id doesn't match any."""
        cloud_account_id = random.randint(9999, 99999)
        context = Context()

        query = """
            query enabledAwsRegionsByCloudAccount ($cloudAccountId: Int!) {
                enabledAwsRegions(cloudAccountId: $cloudAccountId) {
                    __typename
                    ... on AwsRegionsDescribed {
                        enabledRegions
                        disabledRegions
                    }
                    ... on CloudAccountNotFound {
                        message
                    }
                }
            }
        """

        resp = await schema.execute(
            query, context_value=context, variable_values={"cloudAccountId": cloud_account_id}
        )

        assert resp.errors is None
        assert resp.data == {
            "enabledAwsRegions": {
                "__typename": "CloudAccountNotFound",
                "message": "Cloud account could not be found",
            }
        }

    @pytest.mark.asyncio
    @mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
    @mock.patch("api.graphql_app.resolvers.cluster.get_role_arn_of_cloud_account")
    async def test_query_enabled_aws_regions__successful_fetch(
        self,
        mocked_get_role_arn_of_cloud_account: mock.AsyncMock,
        mocked_ec2_ops: mock.MagicMock,
        enforce_strawberry_context_authentication: None,
    ):
        """Test the query enabledAwsRegions for a successful fetch."""
        cloud_account_id = random.randint(9999, 99999)
        cloud_account_role_arn = str(uuid.uuid4())
        regions = list(ClusterRegion)
        enabled_regions = random.sample(regions, k=random.randint(1, len(regions)))

        mocked_ec2_ops.list_enabled_regions = mock.Mock()
        mocked_ec2_ops.list_enabled_regions.return_value = enabled_regions

        mocked_get_role_arn_of_cloud_account.return_value = cloud_account_role_arn

        context = Context()

        query = """
            query enabledAwsRegionsByCloudAccount ($cloudAccountId: Int!) {
                enabledAwsRegions(cloudAccountId: $cloudAccountId) {
                    __typename
                    ... on AwsRegionsDescribed {
                        enabledRegions
                        disabledRegions
                    }
                    ... on CloudAccountNotFound {
                        message
                    }
                }
            }
        """

        resp = await schema.execute(
            query, context_value=context, variable_values={"cloudAccountId": cloud_account_id}
        )

        assert resp.errors is None
        assert resp.data == {
            "enabledAwsRegions": {
                "__typename": "AwsRegionsDescribed",
                "enabledRegions": [region.name for region in enabled_regions],
                "disabledRegions": [region.name for region in regions if region not in enabled_regions],
            }
        }
        mocked_ec2_ops.list_enabled_regions.assert_called_once_with(cloud_account_role_arn)
        mocked_get_role_arn_of_cloud_account.assert_called_once()


class TestAwsNodePicker:
    """Test the queries awsNodePicker and awsNodePickerFilterValues."""

    @pytest.mark.asyncio
    @mock.patch("api.graphql_app.resolvers.cluster.build_connection")
    async def test_query_aws_node_picker(
        self, mocked_build_connection: mock.AsyncMock, enforce_strawberry_context_authentication: None
    ):
        """Test if the query awsNodePicker returns the expect result."""
        node_id = random.randint(1, 1000)
        instance_type = str(uuid.uuid4())
        aws_region = str(uuid.uuid4())
        cpu_manufacturer = str(uuid.uuid4())
        cpu_name = str(uuid.uuid4())
        cpu_arch = str(uuid.uuid4())
        num_cpus = random.randint(1, 100)
        memory = random.randint(1, 100)
        gpu_manufacturer = str(uuid.uuid4())
        gpu_name = str(uuid.uuid4())
        num_gpus = random.randint(1, 100)
        price_per_hour = random.random()

        mocked_build_connection.return_value = Connection(
            edges=[
                Edge(
                    node=AwsNodeTypes(
                        id=node_id,
                        instance_type=instance_type,
                        aws_region=aws_region,
                        cpu_manufacturer=cpu_manufacturer,
                        cpu_name=cpu_name,
                        cpu_arch=cpu_arch,
                        num_cpus=num_cpus,
                        memory=memory,
                        gpu_manufacturer=gpu_manufacturer,
                        gpu_name=gpu_name,
                        num_gpus=num_gpus,
                        price_per_hour=price_per_hour,
                    ),
                    cursor=base64.b64encode(f"{id(uuid.uuid4())}".encode("utf-8")).decode(),
                )
            ],
            total=1,
            page_info=PageInfo(
                has_previous_page=False, has_next_page=False, start_cursor=None, end_cursor=None
            ),
        )
        context = Context()

        query = """
            query {
                awsNodePicker {
                    edges {
                        node {
                            id
                            instanceType
                            awsRegion
                            cpuManufacturer
                            cpuName
                            cpuArch
                            numCpus
                            memory
                            gpuManufacturer
                            gpuName
                            numGpus
                            pricePerHour
                        }
                    }
                }
            }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data is not None
        mocked_build_connection.assert_called_once()

        node = resp.data.get("awsNodePicker").get("edges")[0].get("node")
        assert node.get("id") == node_id
        assert node.get("instanceType") == instance_type
        assert node.get("awsRegion") == aws_region
        assert node.get("cpuManufacturer") == cpu_manufacturer
        assert node.get("cpuName") == cpu_name
        assert node.get("cpuArch") == cpu_arch
        assert node.get("numCpus") == num_cpus
        assert node.get("memory") == memory
        assert node.get("gpuManufacturer") == gpu_manufacturer
        assert node.get("gpuName") == gpu_name
        assert node.get("numGpus") == num_gpus
        assert node.get("pricePerHour") == price_per_hour

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "filter_values",
        [
            ["alpha", "beta", "gamma"],
            ["1000", "4", "2", "8375", "98134264522222"],
            ["4.2", "4.9175354", "0.99991111836464"],
        ],
    )
    @mock.patch("api.graphql_app.resolvers.cluster.build_connection")
    async def test_query_aws_node_picker_filter_values(
        self,
        mocked_build_connection: mock.AsyncMock,
        filter_values: list[str],
        enforce_strawberry_context_authentication: None,
    ):
        """Test if the query awsNodePickerFilterValues returns the expect result."""
        filter_name = str(uuid.uuid4())

        mocked_build_connection.return_value = Connection(
            edges=[
                Edge(
                    node=AwsNodesFilters(
                        filter_name=filter_name,
                        filter_values=filter_values,
                    ),
                    cursor=base64.b64encode(f"{id(uuid.uuid4())}".encode("utf-8")).decode(),
                )
            ],
            total=1,
            page_info=PageInfo(
                has_previous_page=False, has_next_page=False, start_cursor=None, end_cursor=None
            ),
        )
        context = Context()

        query = """
            query {
                awsNodePickerFilterValues {
                    edges {
                        node {
                            filterName
                            filterValues
                        }
                    }
                }
            }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data is not None
        mocked_build_connection.assert_called_once()

        node = resp.data.get("awsNodePickerFilterValues").get("edges")[0].get("node")
        assert node.get("filterName") == filter_name
        assert node.get("filterValues") == filter_values


class TestUploadSlurmConfig:
    """Test the mutation uploadSlurmConfig."""

    @pytest.mark.asyncio
    async def test_insert_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test insert slurm config data."""
        query: str | Select
        client_id = seed_database.cluster_without_storage.client_id

        context = Context()

        query = """
            mutation(
                $config: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmConfig(
                    clientId: $clientId
                    config: $config
                ) {
                    __typename
                    ... on UploadSlurmConfigSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "config": {
                "SwitchType": "switch/null",
                "SlurmUser": "slurm(64030)",
                "TmpFS": "/tmp",
                "UsePam": "No",
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmConfig": {
                "__typename": "UploadSlurmConfigSuccess",
                "message": "Slurm config uploaded successfully",
            }
        }

        async with get_session() as sess:
            query = select(SlurmClusterConfig).where(
                SlurmClusterConfig.cluster_name == seed_database.cluster_without_storage.name
            )
            slurm_config: SlurmClusterConfig | None = (await sess.execute(query)).scalar_one_or_none()
            assert slurm_config is not None
            assert slurm_config.cluster_name == seed_database.cluster_without_storage.name
            assert slurm_config.info == variables["config"]

    @pytest.mark.asyncio
    async def test_add_new_data_fields(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test add new fields to slurm config data when there's already a config in the database."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(SlurmClusterConfig).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "SwitchType": "switch/null",
                        "SlurmUser": "slurm(64030)",
                        "TmpFS": "/tmp",
                        "UsePam": "No",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $config: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmConfig(
                    clientId: $clientId
                    config: $config
                ) {
                    __typename
                    ... on UploadSlurmConfigSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "config": {"SLURM_VERSION": "23.02.7", "SlurmctldPort": "6817", "PreemptExemptTime": "00:00:00"},
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmConfig": {
                "__typename": "UploadSlurmConfigSuccess",
                "message": "Slurm config uploaded successfully",
            }
        }

        async with get_session() as sess:
            query = select(SlurmClusterConfig).where(
                SlurmClusterConfig.cluster_name == seed_database.cluster_without_storage.name
            )
            slurm_config: SlurmClusterConfig | None = (await sess.execute(query)).scalar_one_or_none()
            assert slurm_config is not None
            assert slurm_config.cluster_name == seed_database.cluster_without_storage.name
            assert slurm_config.info == {
                "SLURM_VERSION": "23.02.7",
                "SlurmctldPort": "6817",
                "PreemptExemptTime": "00:00:00",
                "SwitchType": "switch/null",
                "SlurmUser": "slurm(64030)",
                "TmpFS": "/tmp",
                "UsePam": "No",
            }

    @pytest.mark.asyncio
    async def test_replace_data_field_value(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test replace an existing field's value."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(SlurmClusterConfig).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "SwitchType": "switch/null",
                        "SlurmUser": "slurm(64030)",
                        "TmpFS": "/tmp",
                        "UsePam": "No",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $config: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmConfig(
                    clientId: $clientId
                    config: $config
                ) {
                    __typename
                    ... on UploadSlurmConfigSuccess {
                        message
                    }
                }
            }
        """

        variables = {"clientId": client_id, "config": {"TmpFS": "/tmp/new-dir"}}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmConfig": {
                "__typename": "UploadSlurmConfigSuccess",
                "message": "Slurm config uploaded successfully",
            }
        }

        async with get_session() as sess:
            query = select(SlurmClusterConfig).where(
                SlurmClusterConfig.cluster_name == seed_database.cluster_without_storage.name
            )
            slurm_config: SlurmClusterConfig | None = (await sess.execute(query)).scalar_one_or_none()
            assert slurm_config is not None
            assert slurm_config.cluster_name == seed_database.cluster_without_storage.name
            assert slurm_config.info == {
                "SwitchType": "switch/null",
                "SlurmUser": "slurm(64030)",
                "TmpFS": "/tmp/new-dir",
                "UsePam": "No",
            }

    @pytest.mark.asyncio
    async def test_delete_data_field(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test delete a data field."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(SlurmClusterConfig).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "SwitchType": "switch/null",
                        "SlurmUser": "slurm(64030)",
                        "TmpFS": "/tmp",
                        "UsePam": "No",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $config: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmConfig(
                    clientId: $clientId
                    config: $config
                ) {
                    __typename
                    ... on UploadSlurmConfigSuccess {
                        message
                    }
                }
            }
        """

        variables = {"clientId": client_id, "config": {"TmpFS": "/tmp/new-dir", "$delete": ["SwitchType"]}}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmConfig": {
                "__typename": "UploadSlurmConfigSuccess",
                "message": "Slurm config uploaded successfully",
            }
        }

        async with get_session() as sess:
            query = select(SlurmClusterConfig).where(
                SlurmClusterConfig.cluster_name == seed_database.cluster_without_storage.name
            )
            slurm_config: SlurmClusterConfig | None = (await sess.execute(query)).scalar_one_or_none()
            assert slurm_config is not None
            assert slurm_config.cluster_name == seed_database.cluster_without_storage.name
            assert slurm_config.info == {"SlurmUser": "slurm(64030)", "TmpFS": "/tmp/new-dir", "UsePam": "No"}

    @pytest.mark.asyncio
    async def test_insert_data__cluster_does_not_exist(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test insert slurm config data when the cluster does not exist."""
        context = Context()

        query = """
            mutation(
                $config: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmConfig(
                    clientId: $clientId
                    config: $config
                ) {
                    __typename
                    ... on ClusterNotFound {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": str(uuid.uuid4()),
            "config": {
                "SwitchType": "switch/null",
                "SlurmUser": "slurm(64030)",
                "TmpFS": "/tmp",
                "UsePam": "No",
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmConfig": {
                "__typename": "ClusterNotFound",
                "message": "Cluster could not be found.",
            }
        }


class TestUploadSlurmPartitions:
    """Test the mutation uploadSlurmPartitions."""

    @pytest.mark.asyncio
    async def test_insert_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test insert slurm partition data."""
        query: str | Select
        client_id = seed_database.cluster_without_storage.client_id

        context = Context()

        query = """
            mutation(
                $partitions: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmPartitions(
                    clientId: $clientId
                    partitions: $partitions
                ) {
                    __typename
                    ... on UploadSlurmPartitionsSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "partitions": {
                "$replace": {
                    "compute": {
                        "AllowGroups": "ALL",
                        "AllowAccounts": "ALL",
                        "AllowQos": "ALL",
                        "State": "DOWN",
                    },
                    "controller": {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    },
                }
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmPartitions": {
                "__typename": "UploadSlurmPartitionsSuccess",
                "message": "Slurm partitions uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllPartitionInfo).where(
                AllPartitionInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_partition_info: AllPartitionInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_partition_info is not None
            assert all_partition_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_partition_info.info == {
                "compute": {
                    "AllowGroups": "ALL",
                    "AllowAccounts": "ALL",
                    "AllowQos": "ALL",
                    "State": "DOWN",
                },
                "controller": {
                    "PriorityJobFactor": "slurm(64030)",
                    "State": "UP",
                    "SelectTypeParameters": "NONE",
                },
            }

            query = select(PartitionModel).where(
                PartitionModel.cluster_name == seed_database.cluster_without_storage.name
            )
            partitions: list[PartitionModel] = (await sess.execute(query)).scalars().all()
            assert len(partitions) == 2
            for partition in partitions:
                assert partition.cluster_name == seed_database.cluster_without_storage.name
                assert partition.name in ["compute", "controller"]
                if partition.name == "compute":
                    assert partition.info == {
                        "AllowGroups": "ALL",
                        "AllowAccounts": "ALL",
                        "AllowQos": "ALL",
                        "State": "DOWN",
                    }
                elif partition.name == "controller":
                    assert partition.info == {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    }

    @pytest.mark.asyncio
    async def test_replace_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test replace existing slurm partition data."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(AllPartitionInfo).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "controller": {
                            "PriorityJobFactor": "slurm(64030)",
                            "State": "UP",
                            "SelectTypeParameters": "NONE",
                        },
                    },
                }
            )
            await sess.execute(query)

            query = insert(PartitionModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "name": "controller",
                    "info": {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $partitions: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmPartitions(
                    clientId: $clientId
                    partitions: $partitions
                ) {
                    __typename
                    ... on UploadSlurmPartitionsSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "partitions": {"controller": {"State": "DOWN", "JobDefaults": "(null)"}},
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmPartitions": {
                "__typename": "UploadSlurmPartitionsSuccess",
                "message": "Slurm partitions uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllPartitionInfo).where(
                AllPartitionInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_partition_info: AllPartitionInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_partition_info is not None
            assert all_partition_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_partition_info.info == {
                "controller": {
                    "PriorityJobFactor": "slurm(64030)",
                    "State": "DOWN",
                    "SelectTypeParameters": "NONE",
                    "JobDefaults": "(null)",
                }
            }

            query = select(PartitionModel).where(
                PartitionModel.cluster_name == seed_database.cluster_without_storage.name
            )
            partitions: list[PartitionModel] = (await sess.execute(query)).scalars().all()
            assert len(partitions) == 1
            partition = partitions[0]
            assert partition.cluster_name == seed_database.cluster_without_storage.name
            assert partition.name == "controller"
            assert partition.info == {
                "PriorityJobFactor": "slurm(64030)",
                "State": "DOWN",
                "SelectTypeParameters": "NONE",
                "JobDefaults": "(null)",
            }

    @pytest.mark.asyncio
    async def test_delete_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test delete existing slurm partition data."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(AllPartitionInfo).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "controller": {
                            "PriorityJobFactor": "slurm(64030)",
                            "State": "UP",
                            "SelectTypeParameters": "NONE",
                        },
                    },
                }
            )
            await sess.execute(query)

            query = insert(PartitionModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "name": "controller",
                    "info": {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $partitions: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmPartitions(
                    clientId: $clientId
                    partitions: $partitions
                ) {
                    __typename
                    ... on UploadSlurmPartitionsSuccess {
                        message
                    }
                }
            }
        """

        variables = {"clientId": client_id, "partitions": {"$replace": {}}}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmPartitions": {
                "__typename": "UploadSlurmPartitionsSuccess",
                "message": "Slurm partitions uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllPartitionInfo).where(
                AllPartitionInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_partition_info: AllPartitionInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_partition_info is not None
            assert all_partition_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_partition_info.info == {}

            query = select(PartitionModel).where(
                PartitionModel.cluster_name == seed_database.cluster_without_storage.name
            )
            partitions: list[PartitionModel] = (await sess.execute(query)).scalars().all()
            assert len(partitions) == 0

    @pytest.mark.asyncio
    async def test_replace_data__cluster_does_not_exist(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test replace slurm partition data when the cluster does not exist."""
        context = Context()

        query = """
            mutation(
                $partitions: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmPartitions(
                    clientId: $clientId
                    partitions: $partitions
                ) {
                    __typename
                    ... on ClusterNotFound {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": str(uuid.uuid4()),
            "partitions": {
                "$replace": {
                    "compute": {
                        "AllowGroups": "ALL",
                        "AllowAccounts": "ALL",
                        "AllowQos": "ALL",
                        "State": "DOWN",
                    },
                    "controller": {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    },
                }
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmPartitions": {
                "__typename": "ClusterNotFound",
                "message": "Cluster could not be found.",
            }
        }


class TestUploadSlurmNodes:
    """Test the mutation uploadSlurmNodes."""

    @pytest.mark.asyncio
    async def test_insert_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test insert slurm node data."""
        query: str | Select
        client_id = seed_database.cluster_without_storage.client_id

        context = Context()

        query = """
            mutation(
                $nodes: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmNodes(
                    clientId: $clientId
                    nodes: $nodes
                ) {
                    __typename
                    ... on UploadSlurmNodesSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "nodes": {
                "$replace": {
                    "node1": {
                        "NodeAddr": "10.59.51.10",
                        "RealMemory": "3903",
                        "Sockets": "2",
                        "Partitions": "compute,highmem,gpu",
                    }
                },
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmNodes": {
                "__typename": "UploadSlurmNodesSuccess",
                "message": "Slurm nodes uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllNodeInfo).where(
                AllNodeInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_node_info: AllNodeInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_node_info is not None
            assert all_node_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_node_info.info == {
                "node1": {
                    "NodeAddr": "10.59.51.10",
                    "RealMemory": "3903",
                    "Sockets": "2",
                    "Partitions": "compute,highmem,gpu",
                },
            }

            query = select(NodeModel).where(
                NodeModel.cluster_name == seed_database.cluster_without_storage.name
            )
            nodes: list[NodeModel] = (await sess.execute(query)).scalars().all()
            assert len(nodes) == 1
            node = nodes[0]
            assert node.cluster_name == seed_database.cluster_without_storage.name
            assert node.name == "node1"
            assert node.info == {
                "NodeAddr": "10.59.51.10",
                "RealMemory": "3903",
                "Sockets": "2",
                "Partitions": "compute,highmem,gpu",
            }
            assert node.partition_names == ["compute", "highmem", "gpu"]

    @pytest.mark.asyncio
    async def test_replace_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test replace existing slurm node data."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(AllNodeInfo).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "node1": {
                            "NodeAddr": "10.59.51.10",
                            "RealMemory": "102400",
                            "Sockets": "100",
                            "Partitions": "qtm",
                        },
                        "node2": {
                            "NodeAddr": "10.59.51.11",
                            "RealMemory": "51200",
                            "Sockets": "92",
                            "Partitions": "cfd",
                        },
                    },
                }
            )
            await sess.execute(query)

            query = insert(NodeModel).values(
                [
                    {
                        "cluster_name": seed_database.cluster_without_storage.name,
                        "partition_names": ["qtm"],
                        "name": "node1",
                        "info": {
                            "NodeAddr": "10.59.51.10",
                            "RealMemory": "102400",
                            "Sockets": "100",
                            "Partitions": "qtm",
                        },
                    },
                    {
                        "cluster_name": seed_database.cluster_without_storage.name,
                        "partition_names": ["cfd"],
                        "name": "node2",
                        "info": {
                            "NodeAddr": "10.59.51.11",
                            "RealMemory": "51200",
                            "Sockets": "92",
                            "Partitions": "sat",
                        },
                    },
                ]
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $nodes: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmNodes(
                    clientId: $clientId
                    nodes: $nodes
                ) {
                    __typename
                    ... on UploadSlurmNodesSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "nodes": {
                "node1": {"NodeAddr": "10.59.51.17", "Partitions": "eng"},
                "node2": {"NodeAddr": "10.59.51.29", "Partitions": "sat"},
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmNodes": {
                "__typename": "UploadSlurmNodesSuccess",
                "message": "Slurm nodes uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllNodeInfo).where(
                AllNodeInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_node_info: AllNodeInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_node_info is not None
            assert all_node_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_node_info.info == {
                "node1": {
                    "NodeAddr": "10.59.51.17",
                    "RealMemory": "102400",
                    "Sockets": "100",
                    "Partitions": "eng",
                },
                "node2": {
                    "NodeAddr": "10.59.51.29",
                    "RealMemory": "51200",
                    "Sockets": "92",
                    "Partitions": "sat",
                },
            }

            query = select(NodeModel).where(
                NodeModel.cluster_name == seed_database.cluster_without_storage.name
            )
            nodes: list[NodeModel] = (await sess.execute(query)).scalars().all()
            assert len(nodes) == 2
            for node in nodes:
                assert node.cluster_name == seed_database.cluster_without_storage.name
                assert node.name in ["node1", "node2"]
                if node.name == "node1":
                    assert node.partition_names == ["eng"]
                    assert node.info == {
                        "NodeAddr": "10.59.51.17",
                        "RealMemory": "102400",
                        "Sockets": "100",
                        "Partitions": "eng",
                    }
                elif node.name == "node2":
                    assert node.partition_names == ["sat"]
                    assert node.info == {
                        "NodeAddr": "10.59.51.29",
                        "RealMemory": "51200",
                        "Sockets": "92",
                        "Partitions": "sat",
                    }

    @pytest.mark.asyncio
    async def test_delete_data(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test delete existing slurm node data."""
        query: str | Select | Insert
        client_id = seed_database.cluster_without_storage.client_id

        async with get_session() as sess:
            query = insert(AllNodeInfo).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "node1": {
                            "NodeAddr": "10.59.51.10",
                            "RealMemory": "102400",
                            "Sockets": "100",
                            "Partitions": "qtm",
                        },
                        "node2": {
                            "NodeAddr": "10.59.51.11",
                            "RealMemory": "51200",
                            "Sockets": "92",
                            "Partitions": "cfd",
                        },
                    },
                }
            )
            await sess.execute(query)

            query = insert(NodeModel).values(
                [
                    {
                        "cluster_name": seed_database.cluster_without_storage.name,
                        "partition_names": ["qtm"],
                        "name": "node1",
                        "info": {
                            "NodeAddr": "10.59.51.10",
                            "RealMemory": "102400",
                            "Sockets": "100",
                            "Partitions": "qtm",
                        },
                    },
                    {
                        "cluster_name": seed_database.cluster_without_storage.name,
                        "partition_names": ["cfd"],
                        "name": "node2",
                        "info": {
                            "NodeAddr": "10.59.51.11",
                            "RealMemory": "51200",
                            "Sockets": "92",
                            "Partitions": "cfd",
                        },
                    },
                ]
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
            mutation(
                $nodes: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmNodes(
                    clientId: $clientId
                    nodes: $nodes
                ) {
                    __typename
                    ... on UploadSlurmNodesSuccess {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": client_id,
            "nodes": {"node1": {"NodeAddr": "10.59.51.17", "Partitions": "eng"}, "$delete": ["node2"]},
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmNodes": {
                "__typename": "UploadSlurmNodesSuccess",
                "message": "Slurm nodes uploaded successfully",
            }
        }

        time.sleep(5)  # give enough time for async threads to be executed
        async with get_session() as sess:
            query = select(AllNodeInfo).where(
                AllNodeInfo.cluster_name == seed_database.cluster_without_storage.name
            )
            all_node_info: AllNodeInfo | None = (await sess.execute(query)).scalar_one_or_none()
            assert all_node_info is not None
            assert all_node_info.cluster_name == seed_database.cluster_without_storage.name
            assert all_node_info.info == {
                "node1": {
                    "NodeAddr": "10.59.51.17",
                    "RealMemory": "102400",
                    "Sockets": "100",
                    "Partitions": "eng",
                }
            }

            query = select(NodeModel).where(
                NodeModel.cluster_name == seed_database.cluster_without_storage.name
            )
            nodes: list[NodeModel] = (await sess.execute(query)).scalars().all()
            assert len(nodes) == 1
            node = nodes[0]
            assert node.cluster_name == seed_database.cluster_without_storage.name
            assert node.name == "node1"
            assert node.partition_names == ["eng"]
            assert node.info == {
                "NodeAddr": "10.59.51.17",
                "RealMemory": "102400",
                "Sockets": "100",
                "Partitions": "eng",
            }

    @pytest.mark.asyncio
    async def test_replace_data__cluster_does_not_exist(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test replace slurm node data when the cluster does not exist."""
        context = Context()

        query = """
            mutation(
                $nodes: JSONScalar!
                $clientId: String!
            ) {
                uploadSlurmNodes(
                    clientId: $clientId
                    nodes: $nodes
                ) {
                    __typename
                    ... on ClusterNotFound {
                        message
                    }
                }
            }
        """

        variables = {
            "clientId": str(uuid.uuid4()),
            "nodes": {
                "$replace": {
                    "node1": {
                        "NodeAddr": "10.59.51.10",
                        "RealMemory": "3903",
                        "Sockets": "2",
                        "Partitions": "compute,highmem,gpu",
                    }
                },
            },
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "uploadSlurmNodes": {
                "__typename": "ClusterNotFound",
                "message": "Cluster could not be found.",
            }
        }


class TestQuerySlurmInformation:
    """Test all GraphQL queries that return slurm information."""

    @pytest.mark.asyncio
    async def test_query_slurm_config(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the query slurmConfig."""
        query: str | Insert
        async with get_session() as sess:
            query = insert(SlurmClusterConfig).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "info": {
                        "SwitchType": "switch/null",
                        "SlurmUser": "slurm(64030)",
                        "TmpFS": "/tmp",
                        "UsePam": "No",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
        query {
            slurmConfig {
                edges {
                    node {
                        info
                    }
                }
            }
        }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "slurmConfig": {
                "edges": [
                    {
                        "node": {
                            "info": {
                                "SwitchType": "switch/null",
                                "SlurmUser": "slurm(64030)",
                                "TmpFS": "/tmp",
                                "UsePam": "No",
                            }
                        }
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_query_slurm_partitions(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the query slurmPartitions."""
        query: str | Insert
        async with get_session() as sess:
            query = insert(PartitionModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "name": "controller",
                    "info": {
                        "PriorityJobFactor": "slurm(64030)",
                        "State": "UP",
                        "SelectTypeParameters": "NONE",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
        query {
            slurmPartitions {
                edges {
                    node {
                        info
                        name
                    }
                }
            }
        }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "slurmPartitions": {
                "edges": [
                    {
                        "node": {
                            "info": {},
                            "name": "compute",
                        }
                    },
                    {
                        "node": {
                            "info": {
                                "PriorityJobFactor": "slurm(64030)",
                                "State": "UP",
                                "SelectTypeParameters": "NONE",
                            },
                            "name": "controller",
                        }
                    },
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_query_slurm_nodes(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the query slurmNodes."""
        query: str | Insert
        async with get_session() as sess:
            query = insert(NodeModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "partition_names": ["qtm"],
                    "name": "node1",
                    "info": {
                        "NodeAddr": "10.59.51.10",
                        "RealMemory": "102400",
                        "Sockets": "100",
                        "Partitions": "qtm",
                    },
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
        query {
            slurmNodes {
                edges {
                    node {
                        info
                        name
                        partitionNames
                    }
                }
            }
        }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data == {
            "slurmNodes": {
                "edges": [
                    {
                        "node": {
                            "info": {
                                "NodeAddr": "10.59.51.10",
                                "RealMemory": "102400",
                                "Sockets": "100",
                                "Partitions": "qtm",
                            },
                            "name": "node1",
                            "partitionNames": ["qtm"],
                        }
                    }
                ]
            }
        }


class TestAgentHealth:
    """Test all logic related to agent health."""

    @pytest.mark.asyncio
    async def test_query_agent_health(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the query agentHealth."""
        query: str | Insert
        interval = random.randrange(1, 2**31 - 1)
        last_reported = datetime.now(tz=timezone.utc)
        async with get_session() as sess:
            query = insert(AgentHealthCheckModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "interval": interval,
                    "last_reported": last_reported,
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
        query {
            clusters {
                edges {
                    node {
                        name
                        agentHealthCheck {
                            interval
                            lastReported
                            clusterName
                        }
                    }
                }
            }
        }
        """
        variables = {"clusterName": seed_database.cluster_without_storage.name}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        cluster = next(
            filter(
                lambda x: x["node"]["name"] == seed_database.cluster_without_storage.name,
                resp.data["clusters"]["edges"],
            ),
            None,
        )
        assert cluster is not None
        assert cluster["node"]["agentHealthCheck"] == {
            "interval": interval,
            "lastReported": last_reported.isoformat(),
            "clusterName": seed_database.cluster_without_storage.name,
        }

    @pytest.mark.asyncio
    async def test_report_agent_health(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the mutation reportAgentHealth."""
        query: str | Select
        interval = random.randrange(1, 2**31 - 1)

        context = Context()

        query = """
        mutation reportAgentHealth($clientId: String!, $interval: Int!) {
            reportAgentHealth(clientId: $clientId, interval: $interval)
        }
        """
        variables = {
            "clientId": seed_database.cluster_without_storage.client_id,
            "interval": interval,
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {"reportAgentHealth": None}

        async with get_session() as sess:
            query = select(AgentHealthCheckModel).where(
                AgentHealthCheckModel.cluster_name == seed_database.cluster_without_storage.name
            )
            agent_health: AgentHealthCheckModel | None = (await sess.execute(query)).scalar_one_or_none()
            assert agent_health is not None
            assert agent_health.cluster_name == seed_database.cluster_without_storage.name
            assert agent_health.interval == interval

    @pytest.mark.asyncio
    async def test_report_agent_health__on_update(
        self,
        seed_database: SeededData,
        get_session: AsyncGenerator[AsyncSession, None],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the mutation reportAgentHealth when the agent has already reported."""
        query: str | Insert | Select
        interval = random.randrange(1, 2**31 - 1)
        old_last_reported = datetime.now(tz=timezone.utc)

        async with get_session() as sess:
            query = insert(AgentHealthCheckModel).values(
                {
                    "cluster_name": seed_database.cluster_without_storage.name,
                    "interval": interval - 1,
                    "last_reported": old_last_reported,
                }
            )
            await sess.execute(query)
            await sess.commit()

        context = Context()

        query = """
        mutation reportAgentHealth($clientId: String!, $interval: Int!) {
            reportAgentHealth(clientId: $clientId, interval: $interval)
        }
        """
        variables = {
            "clientId": seed_database.cluster_without_storage.client_id,
            "interval": interval,
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {"reportAgentHealth": None}

        async with get_session() as sess:
            query = select(AgentHealthCheckModel).where(
                AgentHealthCheckModel.cluster_name == seed_database.cluster_without_storage.name
            )
            agent_health: AgentHealthCheckModel | None = (await sess.execute(query)).scalar_one_or_none()
            assert agent_health is not None
            assert agent_health.cluster_name == seed_database.cluster_without_storage.name
            assert agent_health.interval == interval
            assert agent_health.last_reported > old_last_reported

    @pytest.mark.asyncio
    async def test_report_agent_health__cluster_not_found(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test the mutation reportAgentHealth when the cluster is not found."""
        query: str | Select
        interval = random.randrange(1, 2**31 - 1)

        context = Context()

        query = """
        mutation reportAgentHealth($clientId: String!, $interval: Int!) {
            reportAgentHealth(clientId: $clientId, interval: $interval)
        }
        """
        variables = {"clientId": str(uuid.uuid4()), "interval": interval}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data == {"reportAgentHealth": None}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "vpc_list",
    [
        (
            [
                {
                    "VpcId": "vpc-123456",
                    "CidrBlock": "10.0.0.0/16",
                    "IsDefault": True,
                    "Tags": [{"Key": "Name", "Value": "Default VPC"}],
                },
                {
                    "VpcId": "vpc-789012",
                    "CidrBlock": "172.16.0.0/16",
                    "IsDefault": False,
                    "Tags": [{"Key": "Name", "Value": "Custom VPC"}],
                },
            ]
        ),
        (
            [
                {
                    "VpcId": "vpc-123456",
                    "CidrBlock": "10.0.0.0/16",
                    "IsDefault": True,
                    "Tags": [],  # No Name tag
                }
            ]
        ),
        ([]),
    ],
)
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_vpcs__check_no_error(
    mocked_ec2_ops: mock.Mock,
    vpc_list: List[Dict],
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the VPCs query returns no error when the user has the required permissions."""
    mocked_ec2_ops.get_vpcs = mock.Mock()
    mocked_ec2_ops.get_vpcs.return_value = vpc_list

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    inject_security_header("me", "compute:vpcs:read")

    graphql_query = """
    query vpcs($cloudAccountId: Int!, $region: ClusterRegion!) {
        vpcs(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on AwsVpcs {
                vpcs {
                    vpcId
                    name
                    cidrBlock
                    isDefault
                }
            }
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("vpcs").get("__typename") == "AwsVpcs"

    expected_vpcs = []
    for vpc in vpc_list:
        name = None
        for tag in vpc.get("Tags", []):
            if tag.get("Key") == "Name":
                name = tag.get("Value")
                break
        expected_vpcs.append(
            {
                "vpcId": vpc["VpcId"],
                "name": name,
                "cidrBlock": vpc["CidrBlock"],
                "isDefault": vpc["IsDefault"],
            }
        )

    assert response_data.get("data").get("vpcs").get("vpcs") == expected_vpcs

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_vpcs__check_param_validation_error(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the VPCs query returns an error when there's a validation error."""
    mocked_ec2_ops.get_vpcs = mock.Mock()
    mocked_ec2_ops.get_vpcs.side_effect = ParamValidationError(report="Dummy error message")

    inject_security_header("me", "compute:vpcs:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query vpcs($cloudAccountId: Int!, $region: ClusterRegion!) {
        vpcs(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on ParameterValidationError {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("vpcs").get("__typename") == "ParameterValidationError"
    assert (
        response_data.get("data").get("vpcs").get("message")
        == "Parameter validation failed:\nDummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_vpcs__check_unauthorized_operation(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the VPCs query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_vpcs = mock.Mock()
    mocked_ec2_ops.get_vpcs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "UnauthorizedOperation",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_vpcs",
    )

    inject_security_header("me", "compute:vpcs:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query vpcs($cloudAccountId: Int!, $region: ClusterRegion!) {
        vpcs(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("vpcs").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("vpcs").get("message") == (
        "An error occurred (UnauthorizedOperation) when calling"
        " the describe_vpcs operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_vpcs__check_access_denied(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the VPCs query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_vpcs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_vpcs",
    )

    inject_security_header("me", "compute:vpcs:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query vpcs($cloudAccountId: Int!, $region: ClusterRegion!) {
        vpcs(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("vpcs").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("vpcs").get("message") == (
        "An error occurred (AccessDenied) when calling the describe_vpcs operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
async def test_query_vpcs__cloud_account_not_found(
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test whether the VPCs query returns the type InvalidInput when the cloud account doesn't exist."""
    inject_security_header("me", "compute:vpcs:read")

    graphql_query = """
    query vpcs($cloudAccountId: Int!, $region: ClusterRegion!) {
        vpcs(cloudAccountId: $cloudAccountId, region: $region) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {"query": graphql_query, "variables": {"cloudAccountId": 100, "region": "us_west_2"}}

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("vpcs").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("vpcs").get("message") == "Cloud account not found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subnet_list",
    [
        (
            [
                {
                    "SubnetId": "subnet-123456",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailabilityZone": "us-west-2a",
                    "Tags": [{"Key": "Name", "Value": "Public Subnet"}],
                },
                {
                    "SubnetId": "subnet-789012",
                    "CidrBlock": "10.0.2.0/24",
                    "AvailabilityZone": "us-west-2b",
                    "Tags": [{"Key": "Name", "Value": "Private Subnet"}],
                },
            ]
        ),
        (
            [
                {
                    "SubnetId": "subnet-123456",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailabilityZone": "us-west-2a",
                    "Tags": [],  # No Name tag
                }
            ]
        ),
        ([]),
    ],
)
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_subnets__check_no_error(
    mocked_ec2_ops: mock.Mock,
    subnet_list: List[Dict],
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the subnets query returns no error when the user has the required permissions."""
    mocked_ec2_ops.get_subnets = mock.Mock()
    mocked_ec2_ops.get_subnets.return_value = subnet_list

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    inject_security_header("me", "compute:subnets:read")

    graphql_query = """
    query subnets($cloudAccountId: Int!, $region: ClusterRegion!, $vpcId: String!) {
        subnets(cloudAccountId: $cloudAccountId, region: $region, vpcId: $vpcId) {
            __typename
            ... on AwsSubnets {
                subnets {
                    subnetId
                    name
                    cidrBlock
                    avZone
                }
            }
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2", "vpcId": "vpc-123456"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("subnets").get("__typename") == "AwsSubnets"

    expected_subnets = []
    for subnet in subnet_list:
        name = None
        for tag in subnet.get("Tags", []):
            if tag.get("Key") == "Name":
                name = tag.get("Value")
                break
        expected_subnets.append(
            {
                "subnetId": subnet["SubnetId"],
                "name": name,
                "cidrBlock": subnet["CidrBlock"],
                "avZone": subnet["AvailabilityZone"],
            }
        )

    assert response_data.get("data").get("subnets").get("subnets") == expected_subnets

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_subnets__check_param_validation_error(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the subnets query returns an error when there's a validation error."""
    mocked_ec2_ops.get_subnets = mock.Mock()
    mocked_ec2_ops.get_subnets.side_effect = ParamValidationError(report="Dummy error message")

    inject_security_header("me", "compute:subnets:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query subnets($cloudAccountId: Int!, $region: ClusterRegion!, $vpcId: String!) {
        subnets(cloudAccountId: $cloudAccountId, region: $region, vpcId: $vpcId) {
            __typename
            ... on ParameterValidationError {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2", "vpcId": "vpc-123456"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("subnets").get("__typename") == "ParameterValidationError"
    assert (
        response_data.get("data").get("subnets").get("message")
        == "Parameter validation failed:\nDummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_subnets__check_unauthorized_operation(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the subnets query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_subnets = mock.Mock()
    mocked_ec2_ops.get_subnets.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "UnauthorizedOperation",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_subnets",
    )

    inject_security_header("me", "compute:subnets:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query subnets($cloudAccountId: Int!, $region: ClusterRegion!, $vpcId: String!) {
        subnets(cloudAccountId: $cloudAccountId, region: $region, vpcId: $vpcId) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2", "vpcId": "vpc-123456"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("subnets").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("subnets").get("message") == (
        "An error occurred (UnauthorizedOperation) when calling"
        " the describe_subnets operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.cluster.ec2_ops")
async def test_query_subnets__check_access_denied(
    mocked_ec2_ops: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test whether the subnets query returns an error when the user doesn't have the required permissions."""
    mocked_ec2_ops.get_subnets.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "Dummy error message",
            }
        },
        operation_name="describe_subnets",
    )

    inject_security_header("me", "compute:subnets:read")

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "dummy",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {
                        "role_arn": "arn:aws:iam::123456789012:role/dummy",
                    },
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    graphql_query = """
    query subnets($cloudAccountId: Int!, $region: ClusterRegion!, $vpcId: String!) {
        subnets(cloudAccountId: $cloudAccountId, region: $region, vpcId: $vpcId) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": cloud_account_id, "region": "us_west_2", "vpcId": "vpc-123456"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("subnets").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("subnets").get("message") == (
        "An error occurred (AccessDenied) when calling the describe_subnets operation: Dummy error message"
    )

    async with get_session() as sess:
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
async def test_query_subnets__cloud_account_not_found(
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test whether the subnets query returns the type InvalidInput when the cloud account doesn't exist."""
    inject_security_header("me", "compute:subnets:read")

    graphql_query = """
    query subnets($cloudAccountId: Int!, $region: ClusterRegion!, $vpcId: String!) {
        subnets(cloudAccountId: $cloudAccountId, region: $region, vpcId: $vpcId) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }
    """

    payload = {
        "query": graphql_query,
        "variables": {"cloudAccountId": 100, "region": "us_west_2", "vpcId": "vpc-123456"},
    }

    response = await test_client.post("/cluster/graphql", json=payload)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    assert response_data.get("data").get("subnets").get("__typename") == "InvalidInput"
    assert response_data.get("data").get("subnets").get("message") == "Cloud account not found"
