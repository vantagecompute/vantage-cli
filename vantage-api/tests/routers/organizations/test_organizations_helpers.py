"""Core module for testing the organizations helpers."""
import itertools
import uuid
from collections.abc import Callable
from textwrap import dedent
from typing import AsyncContextManager, AsyncGenerator
from unittest import mock

import pytest
from fastapi import HTTPException, status
from httpx import HTTPStatusError, Response
from respx.router import MockRouter
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, Select

from api.identity.management_api import backend_client
from api.routers.organizations.helpers import (
    ListGroupsSortFieldChecker,
    ListIdPsSortFilterChecker,
    ListInvitationsSortFieldChecker,
    ListUsersFromOrganizationSortFieldChecker,
    add_admin_user_and_set_up_permissions,
    assign_group_to_user_by_group_name,
    count_members_of_organization,
    generate_azure_config,
    generate_github_config,
    generate_google_config,
    has_organization_reached_user_limit,
    is_cloud_accounts_available_for_deletion,
    is_email_allocated_to_other_account,
    is_organization_name_available,
    notify_users_about_org_deletion,
    parse_org_name,
    sort_field_exception,
    update_inviter_id,
)
from api.sql_app import models
from api.sql_app.enums import SubscriptionTierSeats, SubscriptionTypesNames
from api.sql_app.models import SubscriptionModel, SubscriptionTierModel, SubscriptionTypeModel
from api.sql_app.session import keycloak_transaction


def test_sort_field_exception__check_if_422_is_raised():
    """Check if 422 is raised by the sort field exception."""
    assert isinstance(sort_field_exception, HTTPException)
    assert sort_field_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "checker_class",
    [
        ListUsersFromOrganizationSortFieldChecker,
        ListIdPsSortFilterChecker,
        ListGroupsSortFieldChecker,
        ListInvitationsSortFieldChecker,
    ],
)
def test_field_checker__check_if_available_fields_are_from_the_checker_model(checker_class):
    """Check if available fields are from the checker model."""
    checker = checker_class()

    assert checker.available_fields() == list(checker._model.__fields__.keys())


@pytest.mark.parametrize(
    "checker_class",
    [
        ListUsersFromOrganizationSortFieldChecker,
        ListIdPsSortFilterChecker,
        ListGroupsSortFieldChecker,
        ListInvitationsSortFieldChecker,
    ],
)
def test_field_checker__check_if_available_fields_are_returned_when_called(checker_class):
    """Check if available fields are returned when called."""
    checker = checker_class()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


@pytest.mark.parametrize(
    "checker_class",
    [
        ListUsersFromOrganizationSortFieldChecker,
        ListIdPsSortFilterChecker,
        ListGroupsSortFieldChecker,
        ListInvitationsSortFieldChecker,
    ],
)
def test_field_checker__check_if_none_sort_field_returns_none(checker_class):
    """Check if none sort field returns none."""
    checker = checker_class()

    assert checker(None) is None


@pytest.mark.parametrize(
    "checker_class",
    [
        ListUsersFromOrganizationSortFieldChecker,
        ListIdPsSortFilterChecker,
        ListGroupsSortFieldChecker,
        ListInvitationsSortFieldChecker,
    ],
)
def test_field_checker__check_if_no_available_field_raises_error_when_called(checker_class):
    """Check if no available field raises error when called."""
    checker = checker_class()

    dummy_field = "the_lakers_are_awesome_and_seahawks_arent"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)


@pytest.mark.parametrize(
    "input_value,expected_output_value",
    [
        ("Dummy Name", "dummy-name"),
        ("This one Contains some SymbOls $#@!%&$)(^*)", "this-one-contains-some-symbols"),
        (
            "こんにちは This one has non-ASCII chars 日本人中國的你好안녕하세요",
            "this-one-has-non-ascii-chars",
        ),
        (
            "Test TłchǫłèüñãíçôãäöêïþæœßðýøåšžėįęėūųȯȧḍḳṇṃṛṣṭṇḷḻḥẓẕẖỳỵỹỷṳṷṻḿńǹňȵɲᶇḹỹŀḻḻṫḑḍḏḌḐḑḓḕḗḙḛḝḟḡḠĝğĜĞḡġḢḣḤḥḦḧḨḩḪḫḰḱḲḳḴḵḶḷḸḹḺḻḼḽḾḿṀṁṂṃṈṉṊṋṌṍṎṏṐṑṒṓṔṕṖṗṘṙṚṛṜṝṞṟ",  # noqa: E501
            "test-tchoeunaicoaaoeiyaszeieeuuoadknmrstnllhzzhyyyyuuumnnnlyllltdddddddeeeeefgggggggghhhhhhhhhhkkkkkkllllllllmmmmmmnnnnoooooooopppprrrrrrrr",
        ),
        ("Numb3rs will p4ss", "numb3rs-will-p4ss"),
        ("", ""),
        ("こんにちは", ""),
        ("@#$%^", ""),
        ("- example ", "example"),
        ("d0ub#le_example", "d0uble-example"),
        ("_héllo 'quote'", "hello-quote"),
        (" end with undercore_", "end-with-undercore"),
    ],
)
def test_parse_organization_name(input_value: str, expected_output_value: str):
    """Test that the organization name is parsed correctly."""
    output_value = parse_org_name(input_value)
    assert output_value == expected_output_value


@pytest.mark.parametrize(
    "client_id,client_secret,app_identifier,org_id",
    [
        ("dummy-client-id", "dummy-client-secret", "dummy-app-identifier", "dummy-organization-id"),
        ("", "", "", ""),
        ("", "dummy-client-secret", "dummy-app-identifier", "dummy-organization-id"),
        ("dummy-client-id", "", "dummy-app-identifier", "dummy-organization-id"),
        ("dummy-client-id", "dummy-client-secret", "", "dummy-organization-id"),
        ("dummy-client-id", "dummy-client-secret", "dummy-app-identifier", ""),
        (123456, 123456, 123456, "whatever"),
    ],
)
def test_generate_idp_config(client_id: str, client_secret: str, app_identifier: str, org_id: str):
    """Test that the IdPs configs are generated correctly."""
    azure_config = generate_azure_config(client_id, client_secret, app_identifier, org_id)
    assert azure_config == {
        "alias": org_id,
        "providerId": "microsoft",
        "enabled": True,
        "updateProfileFirstLoginMode": "on",
        "trustEmail": True,
        "storeToken": True,
        "addReadTokenRoleOnCreate": False,
        "authenticateByDefault": False,
        "linkOnly": False,
        "firstBrokerLoginFlowAlias": "existing user",
        "config": {
            "hideOnLoginPage": "true",
            "clientId": client_id,
            "acceptsPromptNoneForwardFromClient": "false",
            "disableUserInfo": "false",
            "tenantId": app_identifier,
            "filteredByClaim": "false",
            "syncMode": "FORCE",
            "clientSecret": client_secret,
        },
    }

    github_config = generate_github_config(client_id, client_secret, org_id)
    assert github_config == {
        "alias": org_id,
        "providerId": "github",
        "enabled": True,
        "updateProfileFirstLoginMode": "on",
        "trustEmail": True,
        "storeToken": True,
        "addReadTokenRoleOnCreate": False,
        "authenticateByDefault": False,
        "linkOnly": False,
        "firstBrokerLoginFlowAlias": "existing user",
        "config": {
            "hideOnLoginPage": "true",
            "clientId": client_id,
            "acceptsPromptNoneForwardFromClient": "false",
            "disableUserInfo": "false",
            "syncMode": "FORCE",
            "clientSecret": client_secret,
        },
    }

    google_config = generate_google_config(client_id, client_secret, org_id)
    assert google_config == {
        "alias": org_id,
        "providerId": "google",
        "enabled": True,
        "updateProfileFirstLoginMode": "on",
        "trustEmail": True,
        "storeToken": True,
        "addReadTokenRoleOnCreate": False,
        "authenticateByDefault": False,
        "linkOnly": False,
        "firstBrokerLoginFlowAlias": "existing user",
        "config": {
            "hideOnLoginPage": "true",
            "clientId": client_id,
            "acceptsPromptNoneForwardFromClient": "false",
            "disableUserInfo": "false",
            "syncMode": "FORCE",
            "userIp": "false",
            "clientSecret": client_secret,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_add_admin_user_and_set_up_permissions__no_error(respx_mock: MockRouter, organization_id: str):
    """Test if the admin user is added and the permissions are set up correctly."""
    group_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    respx_mock.get("/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}).mock(
        return_value=Response(200, json=[{"id": group_id}])
    )
    respx_mock.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}").mock(
        return_value=Response(204)
    )
    respx_mock.post(f"/admin/realms/vantage/organizations/{organization_id}/members/").mock(
        return_value=Response(204)
    )

    await add_admin_user_and_set_up_permissions(user_id, organization_id)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_add_admin_user_and_set_up_permissions__check_get_group_http_error(
    respx_mock: MockRouter, organization_id: str
):
    """Test if the add_admin_user_and_set_up_permissions function raises error on HTTP error getting the Full Admin group."""  # noqa: E501
    user_id = str(uuid.uuid4())

    respx_mock.get("/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}).mock(
        return_value=Response(500)
    )

    with pytest.raises(HTTPStatusError):
        await add_admin_user_and_set_up_permissions(user_id, organization_id)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_add_admin_user_and_set_up_permissions__check_add_user_to_group_http_error(
    respx_mock: MockRouter, organization_id: str
):
    """Test if the add_admin_user_and_set_up_permissions function raises error on HTTP error adding the user to the Full Admin group."""  # noqa: E501
    group_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    respx_mock.get("/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}).mock(
        return_value=Response(200, json=[{"id": group_id}])
    )
    respx_mock.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}").mock(
        return_value=Response(500)
    )

    with pytest.raises(HTTPStatusError):
        await add_admin_user_and_set_up_permissions(user_id, organization_id)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_add_admin_user_and_set_up_permissions__check_add_to_org_http_error(
    respx_mock: MockRouter, organization_id: str
):
    """Test if the add_admin_user_and_set_up_permissions function raises error on HTTP error adding the user to the organization."""  # noqa: E501
    group_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    respx_mock.get("/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}).mock(
        return_value=Response(200, json=[{"id": group_id}])
    )
    respx_mock.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}").mock(
        return_value=Response(204)
    )
    respx_mock.post(f"/admin/realms/vantage/organizations/{organization_id}/members/").mock(
        return_value=Response(500)
    )

    with pytest.raises(HTTPStatusError):
        await add_admin_user_and_set_up_permissions(user_id, organization_id)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_add_admin_user_and_set_up_permissions__error_fetching_admin_group(
    respx_mock: MockRouter, organization_id: str
):
    """Test if the add_admin_user_and_set_up_permissions function raises error when not possible to fetch Full Admin group.

    This is the case where Keycloak itself is not configured correctly, so there's no Full Admin group.
    """  # noqa: E501
    user_id = str(uuid.uuid4())

    respx_mock.get("/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}).mock(
        return_value=Response(200, json=[])
    )

    with pytest.raises(
        ValueError, match="Expected one group with the name 'Full Admin' but got more than one or none."
    ):
        await add_admin_user_and_set_up_permissions(user_id, organization_id)


@pytest.mark.asyncio
async def test_is_email_allocated_to_other_account_when_email_doesnt_exist():
    """Test when the supplied email doesn't exist in the database."""
    result = await is_email_allocated_to_other_account("XXXXXXXXXXXXXXXX")
    assert result is False

@pytest.mark.asyncio
async def test_is_email_allocated_to_other_account_when_email_belongs_to_an_organization(
    invitee_id: str, invitee_email: str, organization_id: str
):
    """Test when the supplied email belongs to an organization."""
    group_id = str(uuid.uuid4())

    async with keycloak_transaction() as conn:
        query = dedent(
            f"""
            INSERT INTO user_entity (id, email)
            VALUES ('{invitee_id}', '{invitee_email}');
            """
        ).strip()
        await conn.execute(query)


        query = dedent(
            f"""
            INSERT INTO keycloak_group (id, name, realm_id, type)
            VALUES ('{group_id}', '{organization_id}', '{uuid.uuid4()}', 1);
            """
        ).strip()
        await conn.execute(query)


        query = dedent(
            f"""
            INSERT INTO user_group_membership (user_id, group_id)
            VALUES ('{invitee_id}', '{group_id}');
            """
        ).strip()

        await conn.execute(query)

    result = await is_email_allocated_to_other_account(invitee_email)
    assert result is True

    async with keycloak_transaction() as conn:
        await conn.execute(f"DELETE FROM keycloak_group WHERE id = '{group_id}';")
        await conn.execute(f"DELETE FROM user_group_membership WHERE group_id = '{group_id}';")
        await conn.execute(f"DELETE FROM user_entity WHERE id = '{invitee_id}';")


@pytest.mark.parametrize("organization_name", ["dummy-1", "dummy-2"])
@pytest.mark.asyncio
async def test_is_organization_name_available_when_name_is_available(organization_name: str):
    """Test when the organization name is available."""
    async with keycloak_transaction() as conn:
        query = dedent(
            f"""
            INSERT INTO org (id, enabled, realm_id, group_id, name, alias )
            VALUES ('{str(uuid.uuid4())}', true, '{str(uuid.uuid4())}', '{str(uuid.uuid4())}', '{organization_name}', '{organization_name}');
            """ #noqa
        ).strip()
        await conn.execute(query)

    result = await is_organization_name_available(organization_name)
    assert result is False

    async with keycloak_transaction() as conn:
        await conn.execute(f"DELETE FROM org WHERE name = '{organization_name}';")


@pytest.mark.parametrize("organization_name", ["dummy-1", "dummy-2"])
@pytest.mark.asyncio
async def test_is_organization_name_available_when_name_is_not_available(organization_name: str):
    """Test when the organization name is not available."""
    result = await is_organization_name_available(organization_name)
    assert result is True


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "email, group_name",
    [
        ("foo@boo.com", "group1"),
        ("baz@zoo.com", "ann2948vnwsdf"),
    ],
)
async def test_assign_group_to_user_by_group_name(email: str, group_name: str, respx_mock: MockRouter):
    """Test the assign_group_to_user_by_group_name function when no error happens."""
    user_id = str(uuid.uuid4())
    group_id = str(uuid.uuid4())

    respx_mock.get(
        "/admin/realms/vantage/users",
        params={
            "briefRepresentation": True,
            "exact": True,
            "email": email,
        },
    ).mock(return_value=Response(200, json=[{"id": user_id}]))
    respx_mock.get(
        "/admin/realms/vantage/groups",
        params={
            "search": group_name,
            "exact": True,
        },
    ).mock(return_value=Response(200, json=[{"id": group_id}]))
    respx_mock.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}").mock(
        return_value=Response(204)
    )

    await assign_group_to_user_by_group_name(email, group_name)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "email, group_name",
    [
        ("foo@boo.com", "group1"),
        ("baz@zoo.com", "ann2948vnwsdf"),
    ],
)
async def test_assign_group_to_user_by_group_name__check_http_error_when_fetching_user_id(
    email: str, group_name: str, respx_mock: MockRouter
):
    """Test the assign_group_to_user_by_group_name function when error happens while fetching the user id."""
    respx_mock.get(
        "/admin/realms/vantage/users",
        params={
            "briefRepresentation": True,
            "exact": True,
            "email": email,
        },
    ).mock(return_value=Response(404, json=[{"error": "not found"}]))

    with pytest.raises(HTTPStatusError):
        await assign_group_to_user_by_group_name(email, group_name)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "email, group_name",
    [
        ("foo@boo.com", "group1"),
        ("baz@zoo.com", "ann2948vnwsdf"),
    ],
)
async def test_assign_group_to_user_by_group_name__check_http_error_when_fetching_group_id(
    email: str, group_name: str, respx_mock: MockRouter
):
    """Test the assign_group_to_user_by_group_name function when error happens while fetching the group id."""
    user_id = str(uuid.uuid4())

    respx_mock.get(
        "/admin/realms/vantage/users",
        params={
            "briefRepresentation": True,
            "exact": True,
            "email": email,
        },
    ).mock(return_value=Response(200, json=[{"id": user_id}]))
    respx_mock.get(
        "/admin/realms/vantage/groups",
        params={
            "search": group_name,
            "exact": True,
        },
    ).mock(return_value=Response(404, json=[{"error": "not found"}]))

    with pytest.raises(HTTPStatusError):
        await assign_group_to_user_by_group_name(email, group_name)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "email, group_name",
    [
        ("foo@boo.com", "group1"),
        ("baz@zoo.com", "ann2948vnwsdf"),
    ],
)
async def test_assign_group_to_user_by_group_name__check_http_error_when_assigning_group(
    email: str, group_name: str, respx_mock: MockRouter
):
    """Test the assign_group_to_user_by_group_name function when error happens while fetching the group id."""
    user_id = str(uuid.uuid4())
    group_id = str(uuid.uuid4())

    respx_mock.get(
        "/admin/realms/vantage/users",
        params={
            "briefRepresentation": True,
            "exact": True,
            "email": email,
        },
    ).mock(return_value=Response(200, json=[{"id": user_id}]))
    respx_mock.get(
        "/admin/realms/vantage/groups",
        params={
            "search": group_name,
            "exact": True,
        },
    ).mock(return_value=Response(200, json=[{"id": group_id}]))
    respx_mock.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}").mock(
        return_value=Response(404)
    )

    with pytest.raises(HTTPStatusError):
        await assign_group_to_user_by_group_name(email, group_name)


@pytest.mark.asyncio
@mock.patch("api.routers.organizations.helpers.fetch_users_count", new_callable=mock.AsyncMock)
async def test_has_organization_reached_user_limit__check_when_there_is_no_subscription(
    mocked_fetch_users_count: mock.AsyncMock,
    sample_uuid: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
):
    """Test the has_organization_reached_user_limit function when there is no subscription."""
    mocked_fetch_users_count.return_value = 5

    result = await has_organization_reached_user_limit(sample_uuid)

    assert result is True
    mocked_fetch_users_count.assert_called_once_with(sample_uuid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "number_of_users, subscription_tier, subscription_type",
    itertools.product(
        [3, 5, 10, 20, 30, 50, 100],
        list(SubscriptionTierSeats),
        list(SubscriptionTypesNames),
    ),
)
@mock.patch("api.routers.organizations.helpers.fetch_users_count", new_callable=mock.AsyncMock)
async def test_has_organization_reached_user_limit__check_when_there_is_subscription(
    mocked_fetch_users_count: mock.AsyncMock,
    number_of_users: int,
    subscription_tier: SubscriptionTierSeats,
    subscription_type: SubscriptionTypesNames,
    sample_uuid: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: Callable[[], None],
):
    """Test the has_organization_reached_user_limit function when there is no subscription."""
    mocked_fetch_users_count.return_value = number_of_users

    async with get_session() as sess:
        query: Select | Insert
        query = select(SubscriptionTierModel.id).where(SubscriptionTierModel.name == subscription_tier.name)
        subscription_tier_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_tier_id is not None

        query = select(SubscriptionTypeModel.id).where(SubscriptionTypeModel.name == subscription_type.name)
        subscription_type_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_type_id is not None

        query = insert(SubscriptionModel).values(
            organization_id=sample_uuid,
            tier_id=subscription_tier_id,
            type_id=subscription_type_id,
            detail_data={},
            is_free_trial=False,
        )
        await sess.execute(query)
        await sess.commit()

    result = await has_organization_reached_user_limit(sample_uuid)

    if subscription_type == SubscriptionTypesNames.aws:
        # cap the AWS subscriptions in the pro level
        if number_of_users >= SubscriptionTierSeats.pro.value:
            assert result is True
        else:
            assert result is False
    else:
        if number_of_users >= subscription_tier.value:
            assert result is True
        else:
            assert result is False
    mocked_fetch_users_count.assert_called_once_with(sample_uuid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "org_id,number_of_members,number_of_clusters",
    [
        ("dummy-organization-id", 1, 0),
        ("another-dummy-id", 1_000, 349),
        ("awesome-coding", 1_000_000, 284_102),
        ("coding-fellowship", 1_000_000_000, 39_999),
        ("1cad1f61-0c94-4539-b77e-50ff780e5932", 20_000, 0),
    ],
)
async def test_count_members_of_organization_helper(
    org_id: str, number_of_members: int, number_of_clusters: int, respx_mock: MockRouter
):
    """Test if counting members of an organization returns the expected number."""
    respx_mock.get(f"/admin/realms/vantage/organizations/{org_id}/members/count").mock(
        return_value=Response(200, json=number_of_members)
    )
    respx_mock.get("admin/realms/vantage/clients", params={"clientId": org_id, "search": True}).mock(
        return_value=Response(200, json=[{"id": "not an uuid"} for _ in range(number_of_clusters)])
    )
    result = await count_members_of_organization(org_id)
    assert result == number_of_members - number_of_clusters


@pytest.mark.asyncio
async def test_count_members_of_organization_helper__when_http_error__count_endpoint(respx_mock: MockRouter):
    """Test if counting members of an organization raises an error when an HTTP error occurs while calling the /members/count endpoint."""  # noqa: E501
    organization_id = "dummy-organization-id"
    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}/members/count").mock(return_value=Response(500))
    with pytest.raises(HTTPStatusError):
        await count_members_of_organization(organization_id)


@pytest.mark.asyncio
async def test_count_members_of_organization_helper__when_http_error__clients_endpoint(
    respx_mock: MockRouter,
):
    """Test if counting members of an organization raises an error when an HTTP error occurs while calling the /clients endpoint."""  # noqa: E501
    organization_id = "dummy-organization-id"
    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}/members/count").mock(
        return_value=Response(200, json=0)
    )
    respx_mock.get("admin/realms/vantage/clients", params={"clientId": organization_id, "search": True}).mock(
        return_value=Response(500)
    )
    with pytest.raises(HTTPStatusError):
        await count_members_of_organization(organization_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "org_id, user_email_list",
    [
        ("dummy-organization-id", [{"email": "foo@boo.com"}]),
        ("another-dummy-id", [{"email": "baz@foo.org"}, {"email": "example@gmail.com"}]),
        ("awesome-coding", []),
    ],
)
@mock.patch("api.routers.organizations.helpers.EMAIL_OPS")
@mock.patch("api.routers.organizations.helpers.count_members_of_organization")
async def test_notify_users_about_org_deletion_helper(
    mocked_count_members_of_organization: mock.MagicMock,
    mocked_email_ops: mock.MagicMock,
    org_id: str,
    user_email_list: list[dict[str, str]],
    respx_mock: MockRouter,
):
    """Test if notifying users about an organization deletion works as expected."""
    mocked_count_members_of_organization.return_value = len(user_email_list)
    mocked_email_ops.send_delete_organization_email = mock.Mock(return_value=None)
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{org_id}/members",
        params={"max": len(user_email_list)}
    ).mock(
        return_value=Response(200, json=user_email_list)
    )

    await notify_users_about_org_deletion(org_id)

    mocked_email_ops.send_delete_organization_email.assert_called_once_with(
        to_addresses=[user["email"] for user in user_email_list]
    )
    mocked_count_members_of_organization.assert_called_once_with(org_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("org_id", ["dummy-organization-id", "another-dummy-id", "awesome-coding"])
@mock.patch("api.routers.organizations.helpers.create_async_session")
async def test_is_cloud_accounts_available_for_deletion__when_no_cloud_accounts(
    mocked_create_async_session: mock.MagicMock, org_id: str, get_session: AsyncGenerator[AsyncSession, None]
):
    """Test if the function returns True when there are no cloud accounts."""
    mocked_create_async_session.return_value = get_session

    result = await is_cloud_accounts_available_for_deletion(organization_id=org_id)

    assert result is True
    mocked_create_async_session.assert_called_once_with(org_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("org_id", ["dummy-organization-id", "another-dummy-id", "awesome-coding"])
@mock.patch("api.routers.organizations.helpers.create_async_session")
async def test_is_cloud_accounts_available_for_deletion__cloud_account_not_in_use(
    mocked_create_async_session: mock.MagicMock,
    org_id: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the function returns True when the cloud account is not in use."""
    mocked_create_async_session.return_value = get_session

    async with get_session() as sess:
        query = insert(models.CloudAccountModel).values(
            {"provider": "aws", "name": "dummy-cloud-account", "attributes": {}}
        )
        await sess.execute(query)
        await sess.commit()

    result = await is_cloud_accounts_available_for_deletion(organization_id=org_id)

    assert result is True
    mocked_create_async_session.assert_called_once_with(org_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("org_id", ["dummy-organization-id", "another-dummy-id", "awesome-coding"])
@mock.patch("api.routers.organizations.helpers.create_async_session")
async def test_is_cloud_accounts_available_for_deletion__cloud_account_in_use_by_cluster(
    mocked_create_async_session: mock.MagicMock,
    org_id: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the function returns False when the cloud account is in use by a cluster."""
    mocked_create_async_session.return_value = get_session

    async with get_session() as sess:
        query = (
            insert(models.CloudAccountModel)
            .values({"provider": "aws", "name": "dummy-cloud-account", "attributes": {}})
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            {
                "name": "dummy-cluster",
                "status": "preparing",
                "client_id": "dummy-client-id",
                "description": "dummy-description",
                "owner_email": "dummy-owner-email",
                "creation_parameters": {},
                "provider": "aws",
                "cloud_account_id": cloud_account_id,
            }
        )
        await sess.execute(query)
        await sess.commit()

    result = await is_cloud_accounts_available_for_deletion(organization_id=org_id)

    assert result is False
    mocked_create_async_session.assert_called_once_with(org_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("org_id", ["dummy-organization-id", "another-dummy-id", "awesome-coding"])
@mock.patch("api.routers.organizations.helpers.create_async_session")
async def test_is_cloud_accounts_available_for_deletion__cloud_account_in_use_by_storage(
    mocked_create_async_session: mock.MagicMock,
    org_id: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the function returns False when the cloud account is in use by a storage."""
    mocked_create_async_session.return_value = get_session

    async with get_session() as sess:
        query = (
            insert(models.CloudAccountModel)
            .values({"provider": "aws", "name": "dummy-cloud-account", "attributes": {}})
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()

        query = insert(models.StorageModel).values(
            {
                "fs_id": "dummy-fs-id",
                "name": "dummy-storage",
                "region": "dummy-region",
                "source": "imported",
                "owner": "dummy-owner",
                "cloud_account_id": cloud_account_id,
            }
        )
        await sess.execute(query)
        await sess.commit()

    result = await is_cloud_accounts_available_for_deletion(organization_id=org_id)

    assert result is False
    mocked_create_async_session.assert_called_once_with(org_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("org_id", ["dummy-organization-id", "another-dummy-id", "awesome-coding"])
@mock.patch("api.routers.organizations.helpers.create_async_session")
async def test_is_cloud_accounts_available_for_deletion__cloud_account_in_use_by_cluster_and_storage(
    mocked_create_async_session: mock.MagicMock,
    org_id: str,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
):
    """Test if the function returns False when the cloud account is in use by many resources."""
    mocked_create_async_session.return_value = get_session

    async with get_session() as sess:
        query = (
            insert(models.CloudAccountModel)
            .values({"provider": "aws", "name": "dummy-cloud-account", "attributes": {}})
            .returning(models.CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()

        query = insert(models.ClusterModel).values(
            {
                "name": "dummy-cluster",
                "status": "preparing",
                "client_id": "dummy-client-id",
                "description": "dummy-description",
                "owner_email": "dummy-owner-email",
                "creation_parameters": {},
                "provider": "aws",
                "cloud_account_id": cloud_account_id,
            }
        )
        await sess.execute(query)

        query = insert(models.StorageModel).values(
            {
                "fs_id": "dummy-fs-id",
                "name": "dummy-storage",
                "region": "dummy-region",
                "source": "imported",
                "owner": "dummy-owner",
                "cloud_account_id": cloud_account_id,
            }
        )
        await sess.execute(query)
        await sess.commit()

    result = await is_cloud_accounts_available_for_deletion(organization_id=org_id)

    assert result is False
    mocked_create_async_session.assert_called_once_with(org_id)


@pytest.mark.asyncio
async def test_update_inviter_id(
    respx_mock: MockRouter,
    requester_email: str,
):
    """Test the update_inviter_id check when the inviter is updated."""
    user_email_test = "test@omnivector.test"
    test_user_id = "test-user-id"

    user_data = {"id": test_user_id, "email": user_email_test, "attributes": {}}

    respx_mock.get(f"/admin/realms/vantage/users?email={user_email_test}").mock(
        return_value=Response(200, json=[user_data]),
    )
    user_data.update({"attributes": {"inviter": requester_email, "walkthrough": "false"}})
    respx_mock.put(f"/admin/realms/vantage/users/{test_user_id}").mock(
        return_value=Response(204),
    )

    update_response = await update_inviter_id(user_email_test, requester_email)

    assert update_response is None
