"""Core module for testing the GraphQL API regarding the storage."""
import itertools
from collections.abc import Callable
from datetime import datetime
from textwrap import dedent
from typing import AsyncContextManager, AsyncGenerator
from unittest import mock

import pytest
from botocore.exceptions import ClientError
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Delete, Insert, Select

from api.graphql_app import schema
from api.graphql_app.helpers import clean_cluster_name
from api.graphql_app.types import Context, Storage
from api.sql_app.enums import (
    CloudAccountEnum,
    StorageSourceEnum,
    SubscriptionTiersNames,
    SubscriptionTierStorageSystems,
    SubscriptionTypesNames,
)
from api.sql_app.models import (
    CloudAccountModel,
    MountPointModel,
    StorageModel,
    SubscriptionModel,
    SubscriptionTierModel,
    SubscriptionTypeModel,
)
from tests.conftest import SeededData


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subscription_tier",
    list(SubscriptionTierStorageSystems),
)
@mock.patch("api.graphql_app.resolvers.storage.create_storage", new_callable=mock.AsyncMock)
async def test_create_storage__check_resource_limit_request__cloud_subscription_type(
    mocked_create_storage: mock.AsyncMock,
    subscription_tier: SubscriptionTierStorageSystems,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    sample_uuid: str,
    enforce_strawberry_context_authentication: None,
    clean_up_database: None,
):
    """Test the createStorage mutation when the user has reached the resource limit.

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

        num_of_storages_to_create = (
            subscription_tier.value
            if subscription_tier != SubscriptionTierStorageSystems.enterprise
            else SubscriptionTierStorageSystems.pro.value + 1
        )

        query = insert(StorageModel).values(
            [
                {
                    "fs_id": f"fs_id{idx}",
                    "name": f"dummy{idx}",
                    "region": "us-west-2",
                    "source": StorageSourceEnum.imported,
                    "owner": "foo@boo.com",
                }
                for idx in range(num_of_storages_to_create)
            ]
        )
        await sess.execute(query)

        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": "dummy__role___arn___"},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        assert cloud_account_id is not None
        await sess.commit()

    mocked_create_storage.return_value = Storage(
        id=1,
        name="testing resource limit",
        fs_id="fs_id1",
        region="us-west-2",
        owner="foo@boo.com",
        source=StorageSourceEnum.imported,
        cloud_account_id=1,
        mount_points=None,
        cloud_account=None,
        created_at=datetime.now(),
    )

    context = Context()

    graphql_query = """
        mutation importStorage {
            createStorage(
                createStorageInput: {
                fsId: "fs-07e3e20af6046bed6"
                name: "quickCreated"
                cloudAccountId: 1
                region: us_west_2
                source: imported
            }
        ) {
            __typename
            ... on Storage {
                id
                fsId
                name
                source
                owner
                cloudAccountId
            }
        }
    }
    """

    resp = await schema.execute(graphql_query, context_value=context)
    if subscription_tier == SubscriptionTierStorageSystems.enterprise:
        assert resp.errors is None
        mocked_create_storage.assert_awaited_once()
    else:
        assert resp.errors is not None
        assert (
            resp.errors[0].message
            == "The resource creation is blocked because it requires a higher subscription tier."
        )
        mocked_create_storage.assert_not_awaited()

    async with get_session() as sess:
        query = delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        await sess.execute(query)
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "num_of_storages_to_create, max_num_of_storages_allowed",
    list(
        itertools.product(
            [
                SubscriptionTierStorageSystems.starter.value - 1,
                SubscriptionTierStorageSystems.starter.value + 1,
                SubscriptionTierStorageSystems.teams.value - 1,
                SubscriptionTierStorageSystems.teams.value + 1,
                SubscriptionTierStorageSystems.pro.value - 1,
                SubscriptionTierStorageSystems.pro.value + 1,
            ],
            [SubscriptionTierStorageSystems.pro.value],
        )
    ),
)
@mock.patch("api.graphql_app.resolvers.storage.create_storage", new_callable=mock.AsyncMock)
async def test_create_storage__check_resource_limit_request__aws_subscription_type(
    mocked_create_storage: mock.AsyncMock,
    num_of_storages_to_create: int,
    max_num_of_storages_allowed: int,
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

        query = insert(StorageModel).values(
            [
                {
                    "fs_id": f"fs_id{idx}",
                    "name": f"dummy{idx}",
                    "region": "us-west-2",
                    "source": StorageSourceEnum.imported,
                    "owner": "foo@boo.com",
                }
                for idx in range(num_of_storages_to_create)
            ]
        )
        await sess.execute(query)

        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": "dummy__role___arn___"},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        assert cloud_account_id is not None
        await sess.commit()

    mocked_create_storage.return_value = Storage(
        id=1,
        name="testing resource limit",
        fs_id="fs_id1",
        region="us-west-2",
        owner="foo@boo.com",
        source=StorageSourceEnum.imported,
        cloud_account_id=1,
        mount_points=None,
        cloud_account=None,
        created_at=datetime.now(),
    )

    context = Context()

    graphql_query = """
        mutation importStorage {
            createStorage(
                createStorageInput: {
                fsId: "fs-07e3e20af6046bed6"
                name: "quickCreated"
                cloudAccountId: 1
                region: us_west_2
                source: imported
            }
        ) {
            __typename
            ... on Storage {
                id
                fsId
                name
                source
                owner
                cloudAccountId
            }
        }
    }
    """

    resp = await schema.execute(graphql_query, context_value=context)
    if num_of_storages_to_create < max_num_of_storages_allowed:
        assert resp.errors is None
        mocked_create_storage.assert_awaited_once()
    else:
        assert resp.errors is not None
        assert (
            resp.errors[0].message
            == "The resource creation is blocked because it requires a higher subscription tier."
        )
        mocked_create_storage.assert_not_awaited()

    async with get_session() as sess:
        query = delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        await sess.execute(query)
        query = delete(CloudAccountModel).where(CloudAccountModel.id == cloud_account_id)
        await sess.execute(query)
        await sess.commit()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__check_duplicated_storage(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    create_dummy_subscription: None,
):
    """Test create a storage record mutation when storage name is duplicated."""
    inject_security_header("me", "storage:file-system:create")

    region = "us_west_2"

    efs_ops_mock.check_efs = mock.Mock()
    efs_ops_mock.create_efs = mock.Mock()

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on DuplicatedStorageName {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": seed_database.storage.name,
                "region": region,
                "source": "imported",
                "cloudAccountId": seed_database.cloud_account.id,
                "fsId": "fs_id1",
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.check_efs.assert_not_called()
    efs_ops_mock.create_efs.assert_not_called()
    assert response_data.get("data").get("createStorage").get("__typename") == "DuplicatedStorageName"
    assert response_data.get("data").get("createStorage").get("message") == "Storage name is already in use"


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__fail_when_fsid_is_not_informed_for_imported_storage(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation when fsid is not informed for imported storage."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.check_efs = mock.Mock(return_value=False)

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "imported",
                "cloudAccountId": cloud_account_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.check_efs.assert_not_called()
    assert response_data.get("data").get("createStorage").get("__typename") == "InvalidInput"
    assert (
        response_data.get("data").get("createStorage").get("message")
        == "The fs_id is required for non-vantage sources"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__fail_when_fsid_is_informed__check_efs_fails(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation when the fsId is informed but the resource is not found on the customer's AWS."""  # noqa: E501
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"
    fs_id = "fs_id1"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.check_efs = mock.Mock(return_value=False)

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on FileSystemMisconfigured {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "imported",
                "cloudAccountId": cloud_account_id,
                "fsId": fs_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.check_efs.assert_called_once_with(fs_id=fs_id, region_name="us-west-2", role_arn=aws_arn)
    assert response_data.get("data").get("createStorage").get("__typename") == "FileSystemMisconfigured"
    assert (
        response_data.get("data").get("createStorage").get("message")
        == "The file system is not tagged with the correct tags or it was not found."
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__error_when_creating_efs(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation when there's error to create the EFS."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.create_efs = mock.Mock(return_value=None)

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on Storage {
                name
                fsId
                createdAt
                owner
                region
                source
                id
                mountPoints {
                    id
                    clusterName
                    clientId
                    storageId
                    mountPoint
                    error
                    status
                    createdAt
                }
            }
            ... on DuplicatedStorageId {
                message
            }
            ... on DuplicatedStorageName {
                message
            }
            ... on MissingAwsPermissions {
                message
            }
            ... on FileSystemMisconfigured {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "vantage",
                "cloudAccountId": cloud_account_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.create_efs.assert_called_once_with(
        fs_name=storage_name, region_name="us-west-2", role_arn=aws_arn
    )
    assert response_data.get("data").get("createStorage").get("__typename") == "UnexpectedBehavior"
    assert (
        response_data.get("data").get("createStorage").get("message")
        == "Was not possible to create the efs. The Efs name conflicts or it's invalid"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__unauthorize_when_creating_efs(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.create_efs = mock.Mock()
    efs_ops_mock.create_efs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "UnauthorizedOperation",
                "Message": "Dummy error message",
            }
        },
        operation_name="create_efs",
    )

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on Storage {
                name
                fsId
                createdAt
                owner
                region
                source
                id
                mountPoints {
                    id
                    clusterName
                    clientId
                    storageId
                    mountPoint
                    error
                    status
                    createdAt
                }
            }
            ... on DuplicatedStorageId {
                message
            }
            ... on DuplicatedStorageName {
                message
            }
            ... on MissingAwsPermissions {
                message
            }
            ... on FileSystemMisconfigured {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "vantage",
                "cloudAccountId": cloud_account_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.create_efs.assert_called_once_with(
        fs_name=storage_name, region_name="us-west-2", role_arn=aws_arn
    )
    assert response_data.get("data").get("createStorage").get("__typename") == "MissingAwsPermissions"
    assert response_data.get("data").get("createStorage").get("message") == (
        "An error occurred (UnauthorizedOperation) when calling"
        " the create_efs operation: Dummy error message"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__access_denied_when_creating_efs(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.create_efs = mock.Mock()
    efs_ops_mock.create_efs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "Dummy error message",
            }
        },
        operation_name="create_efs",
    )

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on Storage {
                name
                fsId
                createdAt
                owner
                region
                source
                id
                mountPoints {
                    id
                    clusterName
                    clientId
                    storageId
                    mountPoint
                    error
                    status
                    createdAt
                }
            }
            ... on DuplicatedStorageId {
                message
            }
            ... on DuplicatedStorageName {
                message
            }
            ... on MissingAwsPermissions {
                message
            }
            ... on FileSystemMisconfigured {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "vantage",
                "cloudAccountId": cloud_account_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.create_efs.assert_called_once_with(
        fs_name=storage_name, region_name="us-west-2", role_arn=aws_arn
    )
    assert response_data.get("data").get("createStorage").get("__typename") == "MissingAwsPermissions"
    assert response_data.get("data").get("createStorage").get("message") == (
        "An error occurred (AccessDenied) when calling" " the create_efs operation: Dummy error message"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__unexpected_when_creating_efs(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    aws_arn = "dummy__role___arn___"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": aws_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.create_efs = mock.Mock()
    efs_ops_mock.create_efs.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "UnknownError",
                "Message": "Dummy error message",
            }
        },
        operation_name="create_efs",
    )

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on Storage {
                name
                fsId
                createdAt
                owner
                region
                source
                id
                mountPoints {
                    id
                    clusterName
                    clientId
                    storageId
                    mountPoint
                    error
                    status
                    createdAt
                }
            }
            ... on DuplicatedStorageId {
                message
            }
            ... on DuplicatedStorageName {
                message
            }
            ... on MissingAwsPermissions {
                message
            }
            ... on FileSystemMisconfigured {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "vantage",
                "cloudAccountId": cloud_account_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.create_efs.assert_called_once_with(
        fs_name=storage_name, region_name="us-west-2", role_arn=aws_arn
    )
    assert response_data.get("data").get("createStorage").get("__typename") == "UnexpectedBehavior"
    assert response_data.get("data").get("createStorage").get("message") == (
        "An error occurred (UnknownError) when calling" " the create_efs operation: Dummy error message"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__create_with_success(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    get_session: AsyncGenerator[AsyncSession, None],
    create_dummy_subscription: None,
):
    """Test create a storage record mutation."""
    inject_security_header("me", "storage:file-system:create")

    role_arn = "arn:aws:iam::000000000000:role/TestVantageAPI"
    storage_name = "EFSStorage"
    fs_id = "fsId1"

    query: str | Insert

    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "name": "DummyCloudAccount",
                    "assisted_cloud_account": False,
                    "description": "dummy",
                    "attributes": {"role_arn": role_arn},
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()
        await sess.commit()

    efs_ops_mock.create_efs = mock.Mock(return_value=fs_id)
    efs_ops_mock.check_efs = mock.Mock(return_value=False)

    query = """
    mutation createStorage(
        $name: String!
        $cloudAccountId: Int!
    ) {
        createStorage(
            createStorageInput: {
                name: $name
                cloudAccountId: $cloudAccountId
                region: us_west_2
            }
        ) {
            __typename
            ... on Storage {
                id
                fsId
                name
                source
                region
                owner
                cloudAccountId
                mountPoints {
                    id
                }
            }
            ... on UnexpectedBehavior {
                message
            }
            ... on InvalidInput {
                message
            }
            ... on DuplicatedStorageName {
                message
            }
            ... on FileSystemMisconfigured {
                message
            }
        }
    }
    """

    body = {
        "query": dedent(query),
        "variables": {
            "name": storage_name,
            "cloudAccountId": cloud_account_id,
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.create_efs.assert_called_once_with(
        fs_name=storage_name, region_name="us-west-2", role_arn=role_arn
    )
    efs_ops_mock.check_efs.assert_not_called()

    assert response_data.get("data").get("createStorage").get("__typename") == "Storage"
    assert response_data.get("data").get("createStorage").get("fsId") == fs_id
    assert response_data.get("data").get("createStorage").get("name") == storage_name
    assert response_data.get("data").get("createStorage").get("region") == "us-west-2"
    assert response_data.get("data").get("createStorage").get("source") == "vantage"
    assert response_data.get("data").get("createStorage").get("mountPoints") == []


@pytest.mark.asyncio
async def test_graphql_update_storage__check_when_storage_is_not_found(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test updating a storage record mutation with storage inexistent."""
    inject_security_header("me", "storage:file-system:update")

    new_name = "NewStorageName"

    query = """\
    mutation updateStorage(
        $id: Int!
        $name: String!
    ) {
        updateStorage(id: $id, name: $name) {
            __typename
            ... on StorageNotFound {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "id": 999,
            "name": new_name,
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("updateStorage")
    assert storage.get("__typename") == "StorageNotFound"
    assert (
        storage.get("message")
        == "Either there's no storage with supplied ID or it belongs to a different owner"
    )


@pytest.mark.asyncio
async def test_graphql_update_storage__check_when_storage_conflicts_for_same_owner(
    inject_security_header: Callable,
    test_client: AsyncClient,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test updating a storage record with a name that conflicts with another cluster from same owner."""
    inject_security_header("me", "storage:file-system:update")

    new_name = "NewStorageName"

    query: str | Insert

    query = """\
    mutation updateStorage(
        $id: Int!
        $name: String!
    ) {
        updateStorage(id: $id, name: $name) {
            __typename
            ... on DuplicatedStorageName {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "id": seed_database.storage.id,
            "name": new_name,
        },
    }

    async with get_session() as session:
        payload = {
            "fs_id": "fs_id1",
            "name": new_name,
            "region": "us-west-2",
            "source": "imported",
            "owner": "tester@omnivector.solutions",
            "cloud_account_id": seed_database.cloud_account.id,
        }
        query = insert(StorageModel).values(**payload).returning()
        await session.execute(query)
        await session.commit()

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("updateStorage")
    assert storage.get("__typename") == "DuplicatedStorageName"
    assert storage.get("message") == f"Storage name {new_name} is already in use"


@pytest.mark.asyncio
async def test_graphql_update_storage__check_when_storage_is_updated(
    inject_security_header: Callable,
    test_client: AsyncClient,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test update a storage record mutation."""
    inject_security_header("me", "storage:file-system:update")

    new_name = "NewStorageName"

    query: str | Select

    query = """\
    mutation updateStorage(
        $id: Int!
        $name: String!
    ) {
        updateStorage(id: $id, name: $name) {
            __typename
            ... on Storage {
                id
                name
                createdAt
                fsId
                owner
                region
                source
                cloudAccountId
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "id": seed_database.storage.id,
            "name": new_name,
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("updateStorage")

    assert storage.get("__typename") == "Storage"
    assert storage.get("name") == new_name

    query = select(StorageModel).where(StorageModel.id == seed_database.storage.id)
    async with get_session() as session:
        storage: StorageModel = (await session.execute(query)).scalar()
    assert storage.name == new_name


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql__delete_storage__check_when_storage_is_not_found(
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test the deleteStorage mutation when the storage is not found."""
    inject_security_header("me", "storage:file-system:delete")

    efs_ops_mock.delete_efs = mock.Mock()

    query = """\
    mutation deleteStorage(
        $storageId: Int!
    ) {
        deleteStorage(storageId: $storageId) {
            __typename
            ... on StorageNotFound {
                message
            }
        }
    }"""

    body = {"query": dedent(query), "variables": {"storageId": 999}}

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("deleteStorage")

    efs_ops_mock.delete_efs.assert_not_called()
    assert storage.get("__typename") == "StorageNotFound"
    assert (
        storage.get("message")
        == f"Either there's no storage with ID {999} or it belongs to a different owner"
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql__delete_storage__check_when_is_deleted(
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test the deleteStorage mutation when the storage is deleted."""
    inject_security_header("me", "storage:file-system:delete")
    efs_ops_mock.delete_efs = mock.Mock()

    query: str | Select

    query = """\
    mutation deleteStorage(
        $storageId: Int!
    ) {
        deleteStorage(storageId: $storageId) {
            __typename
            ... on StorageDeleted {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {"storageId": seed_database.storage.id},
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("data").get("deleteStorage").get("__typename") == "StorageDeleted"
    assert response_data.get("data").get("deleteStorage").get("message") == "Storage has been deleted"
    efs_ops_mock.delete_efs.assert_called_once_with(
        fs_id=seed_database.storage.fs_id,
        region_name=seed_database.storage.region,
        role_arn=seed_database.storage.cloud_account.attributes["role_arn"],
    )

    query = select(func.count()).select_from(StorageModel)
    async with get_session() as session:
        number_of_storages: int = (await session.execute(query)).scalar()

    assert number_of_storages == 1


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_storage_is_not_found(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when the storage is not found."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = seed_database.cluster.name
    fs_id = "unknown_fs_id"
    region = "us_east_1"

    cfn_ops_mock.get_stack_resources = mock.Mock()
    efs_ops_mock.check_mount_point_path = mock.Mock()

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            __typename
            ... on StorageNotFound {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "StorageNotFound"
    assert (
        storage.get("message")
        == "Either there's no storage with supplied ID or it belongs to a different owner"
    )
    cfn_ops_mock.get_stack_resources.assert_not_called()
    efs_ops_mock.check_mount_point_path.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_cluster_is_not_found(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when the cluster is not found."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = "unknown_cluster_name"
    fs_id = "fs_id"
    region = "us_east_1"

    cfn_ops_mock.get_stack_resources = mock.Mock()
    efs_ops_mock.check_mount_point_path = mock.Mock()

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            ... on ClusterNotFound {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "ClusterNotFound"
    assert storage.get("message") == "Cluster could not be found."
    cfn_ops_mock.get_stack_resources.assert_not_called()
    efs_ops_mock.check_mount_point_path.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_storage_already_is_mounted(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when the storage is already mounted in the requested cluster."""
    inject_security_header("me", "storage:mount:create")
    path = seed_database.mount_point.mount_point
    cluster_name = seed_database.cluster.name
    fs_id = seed_database.storage_mounted.fs_id
    region = "us_east_1"

    efs_ops_mock.check_mount_point_path = mock.Mock()
    cfn_ops_mock.get_stack_resources = mock.Mock()

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            __typename
            ... on DuplicatedMountPoint {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "DuplicatedMountPoint"
    assert storage.get("message") == "The storage is already mounted in the requested cluster"
    efs_ops_mock.check_mount_point_path.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_its_not_possible_retrieve_stack_resources(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when it's not possible to retrieve the stack resources."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = seed_database.cluster.name
    fs_id = seed_database.storage.fs_id
    region = "us_west_2"
    credentials = {
        "role_arn": seed_database.storage.cloud_account.attributes["role_arn"],
        "region_name": "us-west-2",
    }

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            __typename
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(return_value=[])
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "UnexpectedBehavior"
    assert storage.get("message") == "Impossible to find the cluster resources to attach the storage"
    efs_ops_mock.check_mount_point_path.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        cfn_config=credentials,
        stack_name=clean_cluster_name(seed_database.cluster.name),
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_get_stack_resources_is_none(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when the stack doesn't exist."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = seed_database.cluster.name
    fs_id = seed_database.storage.fs_id
    region = "us_west_2"
    credentials = {
        "role_arn": seed_database.storage.cloud_account.attributes["role_arn"],
        "region_name": "us-west-2",
    }

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            __typename
            ... on UnexpectedBehavior {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(return_value=None)
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "UnexpectedBehavior"
    assert storage.get("message") == "Impossible to get the stack resources"
    efs_ops_mock.check_mount_point_path.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        cfn_config=credentials,
        stack_name=clean_cluster_name(seed_database.cluster.name),
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__mount_storage__check_when_mount_point_is_not_valid(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the mountStorage mutation when the mount point is not valid."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = seed_database.cluster.name
    fs_id = seed_database.storage.fs_id
    region = "us_west_2"
    instance_id = "instance_id"
    credentials = {
        "role_arn": seed_database.storage.cloud_account.attributes["role_arn"],
        "region_name": "us-west-2",
    }

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            ... on InvalidInput {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(
        return_value=[
            {
                "LogicalResourceId": "HeadNodeInstance",
                "PhysicalResourceId": instance_id,
                "ResourceType": "AWS::EC2::Instance",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "PrivateSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "Vpc",
                "ResourceType": "AWS::EC2::VPC",
                "PhysicalResourceId": "VpcID",
            },
        ]
    )
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("mountStorage")

    assert storage.get("__typename") == "InvalidInput"
    assert storage.get("message") == "Either path to mount is not valid or it's in use by the cluster"
    efs_ops_mock.check_mount_point_path.assert_called_once_with(
        aws_config=credentials, path=path, instance_id=instance_id
    )
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
@mock.patch("api.graphql_app.resolvers.storage._mount_task")
async def test_graphql__mount_storage__check_when_call_return_with_success(
    mount_task_mock: mock.Mock,
    cfn_ops_mock: mock.Mock,
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test the mountStorage mutation when the call returns with success."""
    inject_security_header("me", "storage:mount:create")
    path = "/nfs/foo"
    cluster_name = seed_database.cluster.name
    fs_id = seed_database.storage.fs_id
    region = "us_west_2"
    instance_id = "instance_id"
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}

    query: str | Select

    query = """\
    mutation mountStorage($input: MountStorageInput!) {
        mountStorage(
            mountStorageInput: $input
        ) {
            ... on MountPoint {
                __typename
                id
                clientId
                clusterName
                createdAt
                error
                mountPoint
                status
                storageId
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "fsId": fs_id,
                "clusterName": cluster_name,
                "region": region,
                "path": path,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(
        return_value=[
            {
                "LogicalResourceId": "HeadNodeInstance",
                "PhysicalResourceId": instance_id,
                "ResourceType": "AWS::EC2::Instance",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "PrivateSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "Vpc",
                "ResourceType": "AWS::EC2::VPC",
                "PhysicalResourceId": "VpcID",
            },
        ]
    )
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=True)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None, response_data.get("errors")[0]["message"]
    assert response.status_code == status.HTTP_200_OK

    mount_point_response_data = response_data.get("data").get("mountStorage")

    assert mount_point_response_data.get("__typename") == "MountPoint"

    # fetch supposedly inserted object
    async with get_session() as sess:
        query = select(MountPointModel).where(MountPointModel.id == mount_point_response_data.get("id"))
        mount_point: MountPointModel = (await sess.execute(query)).scalar()

    assert mount_point_response_data.get("storageId") == seed_database.storage.id == mount_point.storage_id
    assert mount_point_response_data.get("clusterName") == cluster_name == mount_point.cluster_name
    assert mount_point_response_data.get("mountPoint") == path == mount_point.mount_point
    assert mount_point_response_data.get("status") == "mounting" == mount_point.status.name
    assert (
        mount_point_response_data.get("clientId") == seed_database.cluster.client_id == mount_point.client_id
    )

    efs_ops_mock.check_mount_point_path.assert_called_once_with(
        aws_config=credentials, path=path, instance_id=instance_id
    )
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__unmount_storage__check_when_mount_point_does_not_exist(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the unmountStorage mutation when the mount point doesn't exist."""
    inject_security_header("me", "storage:mount:delete")
    cluster_name = seed_database.cluster.name

    cfn_ops_mock.get_stack_resources = mock.Mock()
    efs_ops_mock.umount_storage = mock.Mock()

    query = """\
    mutation UmountStorage($input: UnmountStorageInput!) {
    unmountStorage(unmountStorageInput: $input) {
            ... on StorageNotFound {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {"input": {"storageId": 999, "clusterName": cluster_name}},
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("unmountStorage")
    assert storage.get("__typename") == "StorageNotFound"
    assert (
        storage.get("message")
        == f"Either there's no mount point with Storage Id {999} or it belongs to a different owner"  # noqa
    )
    cfn_ops_mock.get_stack_resources.assert_not_called()
    efs_ops_mock.umount_storage.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__unmount_storage__check_when_is_not_possible_to_retrieve_the_stack_resources(
    cfn_ops_mock: mock.Mock,
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the unmountStorage mutation expecting the StorageUnmounting type as response."""
    inject_security_header("me", "storage:mount:delete")
    cluster_name = seed_database.cluster.name
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}

    query = """\
    mutation UmountStorage($input: UnmountStorageInput!) {
    unmountStorage(unmountStorageInput: $input) {
            ... on UnexpectedBehavior {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "storageId": seed_database.storage_mounted.id,
                "clusterName": cluster_name,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(return_value=[])
    efs_ops_mock.umount_storage = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("unmountStorage")
    assert storage.get("__typename") == "UnexpectedBehavior"
    assert storage.get("message") == "Impossible to find the cluster resources to umount the storage"

    efs_ops_mock.umount_storage.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__unmount_storage__check_when_get_stack_resources_is_empty(
    cfn_ops_mock: mock.Mock,
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
):
    """Test the unmountStorage mutation expecting the UnexpectedBehavior type as response."""
    inject_security_header("me", "storage:mount:delete")
    cluster_name = seed_database.cluster.name
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}

    query = """\
    mutation UmountStorage($input: UnmountStorageInput!) {
    unmountStorage(unmountStorageInput: $input) {
            ... on UnexpectedBehavior {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "storageId": seed_database.storage_mounted.id,
                "clusterName": cluster_name,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(return_value=None)
    efs_ops_mock.umount_storage = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("unmountStorage")
    assert storage.get("__typename") == "UnexpectedBehavior"
    assert storage.get("message") == "Impossible to get the stack resources"

    efs_ops_mock.umount_storage.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
@mock.patch("api.graphql_app.resolvers.storage._unmount_task")
async def test_graphql__unmount_storage__check_when_storage_is_unmounted_with_success(
    mount_task_mock: mock.MagicMock,
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database,
):
    """Test the unmountStorage mutation expecting the StorageUnmounting type as response."""
    inject_security_header("me", "storage:mount:delete")
    cluster_name = seed_database.cluster.name
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}
    instance_id = "instance_id"
    vpc_id = "vpc_id"

    query = """\
    mutation UmountStorage($input: UnmountStorageInput!) {
    unmountStorage(unmountStorageInput: $input) {
            ... on StorageUnmounting {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "storageId": seed_database.storage_mounted.id,
                "clusterName": cluster_name,
            }
        },
    }

    cfn_ops_mock.get_stack_resources = mock.Mock(
        return_value=[
            {
                "LogicalResourceId": "HeadNodeInstance",
                "PhysicalResourceId": instance_id,
                "ResourceType": "AWS::EC2::Instance",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::VPC",
                "PhysicalResourceId": vpc_id,
            },
        ]
    )
    efs_ops_mock.umount_storage = mock.Mock(return_value=True)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("unmountStorage")
    assert storage.get("__typename") == "StorageUnmounting"
    assert storage.get("message") == "Storage is being unmounted"

    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__check_mount_point__check_when_cluster_not_found(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    clean_up_database,
):
    """Test the checkMountPoint query expecting the ClusterNotFound type as response."""
    inject_security_header("me", "storage:file-system:read")
    cluster_name = "unknown_cluster"
    path = "/nfs/foo"
    region = "us_west_2"

    cfn_ops_mock.get_stack_resources = mock.Mock()
    efs_ops_mock.check_mount_point_path = mock.Mock()

    query = """\
    query CheckMountPoint($input: CheckMountPointInput!) {
    checkMountPoint(checkMountPoint: $input) {
            __typename
            ... on ClusterNotFound {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "path": path,
                "clusterName": cluster_name,
                "cloudAccountId": seed_database.cloud_account.id,
                "region": region,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("checkMountPoint")
    assert storage.get("__typename") == "ClusterNotFound"
    assert storage.get("message") == "Cluster could not be found."
    cfn_ops_mock.get_stack_resources.assert_not_called()
    efs_ops_mock.check_mount_point_path.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__test_graphql__check_storage__check_when_mount_point_already_exist_for_the_cluster(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    clean_up_database,
):
    """Test the checkMountPoint query when mount point isn't available."""
    inject_security_header("me", "storage:file-system:read")
    cluster_name = seed_database.cluster.name
    path = "/nfs/test"
    region = "us_west_2"

    cfn_ops_mock.get_stack_resources = mock.Mock()
    efs_ops_mock.check_mount_point_path = mock.Mock()

    query = """\
    query CheckMountPoint($input: CheckMountPointInput!) {
    checkMountPoint(checkMountPoint: $input) {
            __typename
            ... on MountPointCheck {
                __typename
                isAvailable
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "path": path,
                "clusterName": cluster_name,
                "cloudAccountId": seed_database.cloud_account.id,
                "region": region,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("checkMountPoint")
    assert storage.get("__typename") == "MountPointCheck"
    assert storage.get("isAvailable") is False
    cfn_ops_mock.get_stack_resources.assert_not_called()
    efs_ops_mock.check_mount_point_path.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__test_graphql__check_storage__check_when_fail_to_retrieve_the_stack_resources(
    cfn_ops_mock: mock.Mock,
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    clean_up_database,
):
    """Test the checkMountPoint query expecting the UnexpectedBehavior type as response."""
    inject_security_header("me", "storage:file-system:read")
    cluster_name = seed_database.cluster.name
    path = "/nfs/foo"
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}

    query = """\
    query CheckMountPoint($path: String!, $clusterName: String!, $cloudAccountId: Int!) {
        checkMountPoint(
            checkMountPoint: {
                path: $path
                clusterName: $clusterName
                region: us_west_2
                cloudAccountId: $cloudAccountId
            }
        ) {
            __typename
            ... on UnexpectedBehavior {
                __typename
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "path": path,
            "clusterName": cluster_name,
            "cloudAccountId": seed_database.cloud_account.id,
        },
    }
    cfn_ops_mock.get_stack_resources = mock.Mock(return_value=[])
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=False)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("checkMountPoint")
    assert storage.get("__typename") == "UnexpectedBehavior"
    assert storage.get("message") == "Impossible to find the cluster resources to check the mount point"
    efs_ops_mock.check_mount_point_path.assert_not_called()
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
@mock.patch("api.graphql_app.resolvers.storage.cfn_ops")
async def test_graphql__check_storage__check_when_path_is_verified(
    cfn_ops_mock: mock.MagicMock,
    efs_ops_mock: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    seed_database: SeededData,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database,
):
    """Test the checkMountPoint query expecting the MountPointCheck type as response."""
    inject_security_header("me", "storage:file-system:read")
    cluster_name = seed_database.cluster.name
    path = "/nfs/foo"
    credentials = {"role_arn": seed_database.cloud_account.attributes["role_arn"], "region_name": "us-west-2"}
    instance_id = "instance_id"

    query = """
    query checkMountPoint($path: String!, $clusterName: String!, $cloudAccountId: Int!) {
        checkMountPoint(
            checkMountPoint: {
                path: $path
                clusterName: $clusterName
                region: us_west_2
                cloudAccountId: $cloudAccountId
            }
            ) {
            __typename
            ... on MountPointCheck {
                isAvailable
            }
            ... on InvalidInput {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
            ... on ClusterNotFound {
                message
            }
        }
    }
    """

    body = {
        "query": dedent(query),
        "variables": {
            "path": path,
            "clusterName": cluster_name,
            "cloudAccountId": seed_database.cloud_account.id,
        },
    }
    cfn_ops_mock.get_stack_resources = mock.Mock(
        return_value=[
            {
                "LogicalResourceId": "HeadNodeInstance",
                "PhysicalResourceId": instance_id,
                "ResourceType": "AWS::EC2::Instance",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::Subnet",
                "PhysicalResourceId": "SubnetID",
            },
            {
                "LogicalResourceId": "PublicSubnet",
                "ResourceType": "AWS::EC2::VPC",
                "PhysicalResourceId": "VpcID",
            },
        ]
    )
    efs_ops_mock.check_mount_point_path = mock.Mock(return_value=True)

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response_data.get("errors") is None
    assert response.status_code == status.HTTP_200_OK

    storage = response_data.get("data").get("checkMountPoint")
    assert storage.get("__typename") == "MountPointCheck"
    assert storage.get("isAvailable") is True
    efs_ops_mock.check_mount_point_path.assert_called_once_with(
        aws_config=credentials, path=path, instance_id=instance_id
    )
    cfn_ops_mock.get_stack_resources.assert_called_once_with(
        stack_name=clean_cluster_name(seed_database.cluster.name),
        cfn_config=credentials,
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.storage.efs_ops")
async def test_graphql_create_storage__check_when_supplied_cloud_account_does_not_exist(
    efs_ops_mock: mock.Mock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    clean_up_database: None,
    create_dummy_subscription: None,
):
    """Test the createStorage mutation by checking when the supplied Cloud Account doesn't exist."""
    inject_security_header("me", "storage:file-system:create")

    storage_name = "EFSStorage"
    region = "us_west_2"
    fs_id = "fs_id1"

    efs_ops_mock.check_efs = mock.Mock(return_value=False)
    efs_ops_mock.create_efs = mock.Mock()

    query = """\
    mutation createStorage(
        $input: CreateStorageInput!
    ) {
        createStorage(createStorageInput: $input) {
            __typename
            ... on InvalidInput {
                message
            }
        }
    }"""

    body = {
        "query": dedent(query),
        "variables": {
            "input": {
                "name": storage_name,
                "region": region,
                "source": "imported",
                "cloudAccountId": 9999999,
                "fsId": fs_id,
            }
        },
    }

    response = await test_client.post("/cluster/graphql", json=body)
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response_data.get("errors") is None
    efs_ops_mock.check_efs.assert_not_called()
    efs_ops_mock.create_efs.assert_not_called()
    assert response_data.get("data").get("createStorage").get("__typename") == "InvalidInput"
    assert (
        response_data.get("data").get("createStorage").get("message")
        == "Cloud account not found with ID provided."
    )
