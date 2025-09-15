"""Core module for testing cloud account endpoints."""
import json
from collections.abc import Callable
from typing import AsyncGenerator
from unittest import mock

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Insert, Select

from api.body.output import CloudAccountModel as CloudAccountPydanticModel
from api.body.output import IamRoleStateEnum
from api.identity.management_api import backend_client
from api.routers.cloud_accounts.helpers import ListCloudAccountsFieldChecker
from api.sql_app.enums import CloudAccountEnum
from api.sql_app.models import CloudAccountApiKeyModel, CloudAccountModel, ClusterModel, StorageModel


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_list_cloud_accounts__empty_database(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns an empty list of results when there's no data in the database."""
    inject_security_header("me")
    response = await test_client.get("/admin/management/cloud_accounts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_list_cloud_accounts__fetch_data(
    get_session: AsyncGenerator[AsyncSession, None],
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test if the endpoint returns the expected list of results."""
    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel)
        cloud_account_row = (await session.execute(query)).fetchone()
        await session.commit()

    inject_security_header("me")
    response = await test_client.get("/admin/management/cloud_accounts")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    cloud_account = CloudAccountPydanticModel.from_orm(cloud_account_row)
    cloud_account.in_use = False
    assert response_data[0] == json.loads(cloud_account.json())


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_list_cloud_accounts__fetch_data_paginated(
    get_session: AsyncGenerator[AsyncSession, None],
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test if the endpoint returns the expected list of results when pagination parameters are sent."""
    cloud_account_row_data_1 = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy1",
        "assisted_cloud_account": False,
        "description": "dummy description 1",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/foo"},
    }
    cloud_account_row_data_2 = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy2",
        "assisted_cloud_account": False,
        "description": "dummy description 2",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/boo"},
    }

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values([cloud_account_row_data_1, cloud_account_row_data_2])
            .returning(CloudAccountModel)
        )
        cloud_account_rows = (await session.execute(query)).fetchall()
        await session.commit()

    inject_security_header("me")
    response = await test_client.get("/admin/management/cloud_accounts", params={"after": 0, "max": 1})

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    assert response_data[0] == json.loads(CloudAccountPydanticModel.from_orm(cloud_account_rows[0]).json())

    response = await test_client.get("/admin/management/cloud_accounts", params={"after": 1, "max": 1})

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    cloud_account_1 = CloudAccountPydanticModel.from_orm(cloud_account_rows[1])
    cloud_account_1.in_use = False
    assert response_data[0] == json.loads(cloud_account_1.json())


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_list_cloud_accounts__fetch_data_by_search(
    get_session: AsyncGenerator[AsyncSession, None],
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test if the endpoint returns the expected result when passing the search query parameter."""
    cloud_account_name = "DummyAccount"

    cloud_account_row_data_1 = {
        "provider": CloudAccountEnum.aws,
        "name": cloud_account_name,
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/foo"},
    }
    cloud_account_row_data_2 = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy2",
        "assisted_cloud_account": False,
        "description": "dummy description 2",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/boo"},
    }

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values([cloud_account_row_data_1, cloud_account_row_data_2])
            .returning(CloudAccountModel)
        )
        cloud_account_rows = (await session.execute(query)).fetchall()
        await session.commit()

    inject_security_header("me")
    response = await test_client.get(
        "/admin/management/cloud_accounts", params={"search": cloud_account_name}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    cloud_account = CloudAccountPydanticModel.from_orm(cloud_account_rows[0])
    cloud_account.in_use = False
    assert response_data[0] == json.loads(cloud_account.json())


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sort_field",
    list(filter(lambda item: item != "in_use", ListCloudAccountsFieldChecker.available_fields())),
)
async def test_list_cloud_accounts__check_sorting_over_fields(
    sort_field: str,
    get_session: AsyncGenerator[AsyncSession, None],
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test if the endpoint returns the expected result when passing the search query parameter."""
    cloud_account_row_data_1 = {
        "provider": CloudAccountEnum.aws,
        "name": f"foo-{sort_field}",
        "assisted_cloud_account": False,
        "description": "aaaaaa123",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/boo"},
    }
    cloud_account_row_data_2 = {
        "provider": CloudAccountEnum.aws,
        "name": f"boo-{sort_field}",
        "assisted_cloud_account": True,
        "description": "bbbbbb123",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/foo"},
    }

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values([cloud_account_row_data_1, cloud_account_row_data_2])
            .returning(CloudAccountModel)
        )
        cloud_account_rows = (await session.execute(query)).fetchall()
        await session.commit()

    inject_security_header("me")
    response = await test_client.get(
        "/admin/management/cloud_accounts", params={"sort_field": sort_field, "sort_ascending": True}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 2
    assert response_data == sorted(
        [json.loads(CloudAccountPydanticModel.from_orm(row).json()) for row in cloud_account_rows],
        key=lambda x: x[sort_field],
        reverse=False,
    )

    response = await test_client.get(
        "/admin/management/cloud_accounts", params={"sort_field": sort_field, "sort_ascending": False}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 2
    assert response_data == sorted(
        [json.loads(CloudAccountPydanticModel.from_orm(row).json()) for row in cloud_account_rows],
        key=lambda x: x[sort_field],
        reverse=True,
    )

    # clean up database because the clean_up_database fixture
    # is not yielded back untill the end of all parameters
    async with get_session() as session:
        await session.execute(delete(CloudAccountModel))
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_get_cloud_account_by_role_arn__no_result_found(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when no result is found."""
    cloud_account_role_arn = "arn:aws:iam::123456789012:role/foo-boo"

    inject_security_header("me")
    response = await test_client.get(f"/admin/management/cloud_accounts/{cloud_account_role_arn}")
    response_data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response_data["message"] == "No cloud account was found with the given role ARN"


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_get_cloud_account_by_role_arn__result_found(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint returns 200 when a result is found.

    This test checks if the endpoint returns a single result event there are multiple results in the database.
    """
    cloud_account_role_arn_1 = "arn:aws:iam::123456789012:role/foo-boo"
    cloud_account_role_arn_2 = "arn:aws:iam::123456789012:role/boo-foo"

    cloud_account_row_data_1 = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy1",
        "assisted_cloud_account": False,
        "description": "dummy description 1",
        "attributes": {"role_arn": cloud_account_role_arn_1},
    }
    cloud_account_row_data_2 = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy2",
        "assisted_cloud_account": False,
        "description": "dummy description 2",
        "attributes": {"role_arn": cloud_account_role_arn_2},
    }

    async with get_session() as session:
        query = (
            insert(CloudAccountModel)
            .values([cloud_account_row_data_1, cloud_account_row_data_2])
            .returning(CloudAccountModel)
        )
        cloud_account_rows = (await session.execute(query)).fetchall()
        await session.commit()

    inject_security_header("me")

    # check if 1st first match is returned
    response = await test_client.get("/admin/management/cloud_accounts/foo")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == json.loads(CloudAccountPydanticModel.from_orm(cloud_account_rows[0]).json())

    # test if the 1st match is returned
    response = await test_client.get("/admin/management/cloud_accounts/boo")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == json.loads(CloudAccountPydanticModel.from_orm(cloud_account_rows[0]).json())

    # test searching for the 2nd match
    response = await test_client.get("/admin/management/cloud_accounts/boo-foo")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == json.loads(CloudAccountPydanticModel.from_orm(cloud_account_rows[1]).json())

    # test if it is possible to pass a "path like" string as parameter
    response = await test_client.get(f"/admin/management/cloud_accounts/{cloud_account_role_arn_1}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == json.loads(CloudAccountPydanticModel.from_orm(cloud_account_rows[0]).json())


@pytest.mark.asyncio
async def test_create_cloud_account__check_non_existent_api_key(
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 403 when the supplied API key doesn't exist."""
    cloud_account_input_data = {
        "name": "DummyCloudAccount",
        "description": "Dummy description",
        "role_arn": "arn:aws:iam::123456789012:role/foo",
        "assisted_cloud_account": True,
        "api_key": "dummy-api-key",
        "organization_id": sample_uuid,
    }
    inject_security_header("me", "admin:cloud-accounts:create")
    response = await test_client.post("/admin/management/cloud_accounts", json=cloud_account_input_data)
    response_data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response_data["message"] == "Bad API key"


@pytest.mark.asyncio
async def test_create_cloud_account__check_mismatch_between_api_key_and_organization_id(
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    get_session: Callable[[], AsyncGenerator[AsyncSession, None]],
    clean_up_database: None,
):
    """Test if the endpoint returns 403 when the supplied API key doesn't match the organization ID."""
    cloud_account_input_data = {
        "name": "DummyCloudAccount",
        "description": "Dummy description",
        "role_arn": "arn:aws:iam::123456789012:role/foo",
        "assisted_cloud_account": True,
        "api_key": "654321",
        "organization_id": sample_uuid,
    }

    async with get_session() as sess:
        query = insert(CloudAccountApiKeyModel).values(api_key="123456", organization_id=sample_uuid)
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me", "admin:cloud-accounts:edit")
    response = await test_client.post("/admin/management/cloud_accounts", json=cloud_account_input_data)
    response_data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response_data["message"] == "Bad API key"


@pytest.mark.asyncio
async def test_create_cloud_account__assisted_cloud_account(
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint correctly creates a Cloud Account in assisted mode."""
    query: Insert | Select
    api_key = "123abc"
    cloud_account_input_data = {
        "name": "DummyCloudAccount",
        "description": "Dummy description",
        "role_arn": "arn:aws:iam::123456789012:role/foo",
        "assisted_cloud_account": True,
        "api_key": api_key,
        "organization_id": sample_uuid,
    }

    async with get_session() as sess:
        query = insert(CloudAccountApiKeyModel).values(api_key=api_key, organization_id=sample_uuid)
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me", "admin:cloud-accounts:edit")
    response = await test_client.post("/admin/management/cloud_accounts", json=cloud_account_input_data)
    response_data = response.json()

    assert response.status_code == status.HTTP_201_CREATED

    async with get_session() as session:
        query = select(CloudAccountModel).where(CloudAccountModel.name == cloud_account_input_data["name"])
        cloud_account_row = (await session.execute(query)).scalar()
        assert cloud_account_row is not None

        query = select(CloudAccountApiKeyModel).where(CloudAccountApiKeyModel.api_key == api_key)
        cloud_account_api_key_row = (await session.execute(query)).scalar_one_or_none()
        assert cloud_account_api_key_row is None

    cloud_account_row_data = CloudAccountPydanticModel.from_orm(cloud_account_row)

    assert cloud_account_row_data.id == response_data["id"]
    assert cloud_account_row_data.name == cloud_account_input_data["name"] == response_data["name"]
    assert (
        cloud_account_row_data.description
        == cloud_account_input_data["description"]
        == response_data["description"]
    )
    assert (
        cloud_account_row_data.assisted_cloud_account
        == cloud_account_input_data["assisted_cloud_account"]
        == response_data["assisted_cloud_account"]
    )
    assert (
        cloud_account_row_data.attributes["role_arn"]
        == cloud_account_input_data["role_arn"]
        == response_data["attributes"]["role_arn"]
    )
    assert cloud_account_row_data.provider == CloudAccountEnum.aws.value == response_data["provider"]


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_cloud_account__non_assisted_cloud_account(
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint correctly creates a Cloud Account in non assisted mode."""
    query: Insert | Select
    api_key = "123abc"
    cloud_account_input_data = {
        "name": "DummyCloudAccount",
        "description": "Dummy description",
        "role_arn": "arn:aws:iam::123456789012:role/foo",
        "assisted_cloud_account": True,
        "api_key": api_key,
        "organization_id": sample_uuid,
    }

    async with get_session() as sess:
        query = insert(CloudAccountApiKeyModel).values(api_key=api_key, organization_id=sample_uuid)
        await sess.execute(query)
        await sess.commit()

    response = await test_client.post("/admin/management/cloud_accounts", json=cloud_account_input_data)
    response_data = response.json()

    assert response.status_code == status.HTTP_201_CREATED

    async with get_session() as session:
        query = select(CloudAccountModel).where(CloudAccountModel.name == cloud_account_input_data["name"])
        cloud_account_row = (await session.execute(query)).scalar()
        assert cloud_account_row is not None

        query = select(CloudAccountApiKeyModel).where(CloudAccountApiKeyModel.api_key == api_key)
        cloud_account_api_key_row = (await session.execute(query)).scalar_one_or_none()
        assert cloud_account_api_key_row is None

    cloud_account_row_data = CloudAccountPydanticModel.from_orm(cloud_account_row)

    assert cloud_account_row_data.id == response_data["id"]
    assert cloud_account_row_data.name == cloud_account_input_data["name"] == response_data["name"]
    assert (
        cloud_account_row_data.description
        == cloud_account_input_data["description"]
        == response_data["description"]
    )
    assert (
        cloud_account_row_data.assisted_cloud_account
        == cloud_account_input_data["assisted_cloud_account"]
        == response_data["assisted_cloud_account"]
    )
    assert (
        cloud_account_row_data.attributes["role_arn"]
        == cloud_account_input_data["role_arn"]
        == response_data["attributes"]["role_arn"]
    )
    assert cloud_account_row_data.provider == CloudAccountEnum.aws.value == response_data["provider"]


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_cloud_account(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint is able to patch the description of a Cloud Account."""
    query: Select | Insert

    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel)
        cloud_account_row = CloudAccountPydanticModel.from_orm((await session.execute(query)).fetchone())
        await session.commit()

    new_description = "just testing"

    inject_security_header("me", "admin:cloud-accounts:update")
    response = await test_client.patch(
        f"/admin/management/cloud_accounts/{cloud_account_row.id}", json={"description": new_description}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK

    async with get_session() as session:
        query = select(CloudAccountModel).where(CloudAccountModel.id == cloud_account_row.id)
        cloud_account_row = (await session.execute(query)).scalar()

    assert cloud_account_row is not None
    assert cloud_account_row.description == new_description == response_data["description"]


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_cloud_account(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint returns 204 after deleting a cloud account."""
    query: Insert | Select
    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel)
        cloud_account_row = CloudAccountPydanticModel.from_orm((await session.execute(query)).fetchone())
        await session.commit()

    inject_security_header("me", "admin:cloud-accounts:delete")
    response = await test_client.delete(f"/admin/management/cloud_accounts/{cloud_account_row.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    async with get_session() as session:
        query = select(CloudAccountModel).where(CloudAccountModel.id == cloud_account_row.id)
        cloud_account_row = (await session.execute(query)).one_or_none()

    assert cloud_account_row is None


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_cloud_account__no_record_in_database(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when deleting a cloud account that doesn't exist."""
    inject_security_header("me", "admin:cloud-accounts:delete")
    response = await test_client.delete("/admin/management/cloud_accounts/1")
    response_data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response_data["message"] == "No cloud account was found with the given ID"


@pytest.mark.parametrize(
    "db_model,db_data",
    [
        (
            StorageModel,
            {
                "fs_id": "fs-dummy",
                "name": "storage-dummy",
                "region": "us-west-2",
                "source": "vantage",
                "cloud_account_id": 0,
                "owner": "owner",
            },
        ),
        (
            ClusterModel,
            {
                "name": "dummy",
                "status": "preparing",
                "client_id": "aws-dummy-id",
                "description": "dummy description",
                "provider": CloudAccountEnum.aws,
                "creation_parameters": {},
                "owner_email": "owner",
                "cloud_account_id": 0,
            },
        ),
    ],
)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_cloud_account_in_use(
    db_model,
    db_data,
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the endpoint returns 400 when deleting a cloud account that is in use by storage or cluster."""
    query: Insert | Select
    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": "arn:aws:iam::123456789012:role/role-name"},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel)
        cloud_account_row = CloudAccountPydanticModel.from_orm((await session.execute(query)).fetchone())

        db_data["cloud_account_id"] = cloud_account_row.id
        query = insert(db_model).values(db_data).returning(db_model)
        await session.execute(query)

        await session.commit()

    inject_security_header("me", "admin:cloud-accounts:delete")
    response = await test_client.delete(f"/admin/management/cloud_accounts/{cloud_account_row.id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    async with get_session() as session:
        query = select(CloudAccountModel).where(CloudAccountModel.id == cloud_account_row.id)
        cloud_account_row = (await session.execute(query)).one_or_none()

    assert cloud_account_row is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_arn",
    [
        "arn:aws:iam::123456789012:role/",  # empty role name
        "arn:aws:iam::12345:role/MyRole1",  # account id doesn't contain 12 digits
        "arn:aws:iam:us-east-1:123456789012:role/MyRole2",  # missing double colons after 'iam'
        "arn:aws:iam::123456789012:rolee/MyRole3",  # typo in 'role'
        "arn:aws:iam::123456789012:role/My_Role$",  # invalid character in role name
        "arn:aws:iam:::role/MyRole5",  # missing account id
        "arm:aws:iam::123456789012:role/MyRole6",  # typo in 'arn'
        "arn:aws:iam::123456789012:role/ThisRoleNameIsWayTooLongAndDefinitelyExceedsTheSixtyFourCharacterLimit",  # role name exceeds 64 chars # noqa: E501
        "arn:aws:iam::123456789012:role/My Role7",  # space in role name
        "xr:aws:iam::123456789012:role/MyRole8",  # typo in 'arn'
        "arn:aws:iam::123456789012:role/deployment/production/application/RoleName",  # nested role path
    ],
)
async def test_check_iam_role__check_malformed_arn(
    role_arn: str, test_client: AsyncClient, inject_security_header: Callable
):
    """Test if the endpoint returns 200 when the role ARN is malformed."""
    inject_security_header("me")
    response = await test_client.get(f"/admin/management/cloud_accounts/check-iam-role/{role_arn}")
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("state") == "MALFORMED_ARN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_arn",
    [
        "arn:aws:iam::123456789012:role/MyRole1",
        "arn:aws:iam::123456789012:role/My-Role_2",
        "arn:aws:iam::123456789012:role/My.Role3",
        "arn:aws:iam::123456789012:role/myrole4",
        "arn:aws:iam::123456789012:role/123MyRole5",
        "arn:aws:iam::123456789012:role/My_Role+Equals",
        "arn:aws:iam::123456789012:role/Role,With,Commas",
        "arn:aws:iam::123456789012:role/Role@Email",
        "arn:aws:iam::123456789012:role/_Role-Start-Underscore",
        "arn:aws:iam::123456789012:role/a123456789012345678901234567890123456789012345678901234567890123",
        "arn:aws:iam::123456789012:role/Role_+=,.@-Role",
        "arn:aws:iam::123456789012:role/1stRoleName",
        "arn:aws:iam::123456789012:role/MyRoleWithMixedCASE",
        "arn:aws:iam::123456789012:role/Role____With____Underscores",
        "arn:aws:iam::123456789012:role/Role----With----Dashes",
        "arn:aws:iam::123456789012:role/RoleName-",
        "arn:aws:iam::123456789012:role/+=,.@-_",
        "arn:aws:iam::123456789012:role/Role123_+=,.@-456",
    ],
)
@mock.patch("api.routers.cloud_accounts.iam_ops")
async def test_check_iam_role__check_valid_arn(
    mocked_iam_ops: mock.MagicMock, role_arn: str, test_client: AsyncClient, inject_security_header: Callable
):
    """Test if the endpoint returns 200 when the role ARN is valid."""
    mocked_iam_ops.check_iam_role_state = mock.AsyncMock(return_value="VALID")
    inject_security_header("me")
    response = await test_client.get(f"/admin/management/cloud_accounts/check-iam-role/{role_arn}")
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("state") == "VALID"
    mocked_iam_ops.check_iam_role_state.assert_awaited_once_with(role_arn)


@pytest.mark.asyncio
@mock.patch("api.routers.cloud_accounts.iam_ops")
async def test_check_iam_role__check_missing_permissions(
    mocked_iam_ops: mock.MagicMock, test_client: AsyncClient, inject_security_header: Callable
):
    """Test if the endpoint returns 200 when the role ARN is valid.

    Note this test doesn't verify the endless options of the role ARN, this was done in the previous tests.
    """
    mocked_iam_ops.check_iam_role_state = mock.AsyncMock(return_value="MISSING_PERMISSIONS")
    inject_security_header("me")
    response = await test_client.get(
        "/admin/management/cloud_accounts/check-iam-role/arn:aws:iam::123456789012:role/MyRole"
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data.get("state") == "MISSING_PERMISSIONS"
    mocked_iam_ops.check_iam_role_state.assert_awaited_once_with("arn:aws:iam::123456789012:role/MyRole")


@pytest.mark.asyncio
@mock.patch("api.routers.cloud_accounts.iam_ops")
async def test_check_iam_role_state__test_when_role_is_in_use(
    mocked_iam_ops: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_session: AsyncGenerator[AsyncSession, None],
):
    """Test function to check the state of the IAM role when it is in use."""
    role_arn = "arn:aws:iam::123456789012:role/MyRole"
    query: Insert | Select
    cloud_account_row_data = {
        "provider": CloudAccountEnum.aws,
        "name": "dummy",
        "assisted_cloud_account": False,
        "description": "dummy description",
        "attributes": {"role_arn": role_arn},
    }

    async with get_session() as session:
        query = insert(CloudAccountModel).values(cloud_account_row_data).returning(CloudAccountModel)
        await session.execute(query)
        await session.commit()

    mocked_iam_ops.check_iam_role_state = mock.AsyncMock(return_value=IamRoleStateEnum.VALID)
    inject_security_header("me")
    response = await test_client.get(f"/admin/management/cloud_accounts/check-iam-role/{role_arn}")
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    mocked_iam_ops.check_iam_role_state.assert_awaited_once_with(role_arn)
    assert response_data.get("state") == "IN_USE"


@pytest.mark.asyncio
@mock.patch("api.routers.cloud_accounts.iam_ops")
async def test_check_iam_role_state__test_when_role_is_not_found_or_not_accessible(
    mocked_iam_ops: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test function to check the state of the IAM role when it is not found or accessible."""
    role_arn = "arn:aws:iam::123456789012:role/MyRole"

    mocked_iam_ops.check_iam_role_state = mock.AsyncMock(
        return_value=IamRoleStateEnum.NOT_FOUND_OR_NOT_ACCESSIBLE
    )

    inject_security_header("me")
    response = await test_client.get(f"/admin/management/cloud_accounts/check-iam-role/{role_arn}")
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    mocked_iam_ops.check_iam_role_state.assert_awaited_once_with(role_arn)
    assert response_data.get("state") == "NOT_FOUND_OR_NOT_ACCESSIBLE"
