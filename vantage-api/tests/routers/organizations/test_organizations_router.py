"""Core module for testing the organizations endpoints."""
import json
import uuid
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Dict, List, Union
from unittest import mock

import pytest
from fastapi import status
from freezegun import freeze_time
from httpx import AsyncClient, Response
from respx.router import MockRouter

from api.body.output import (
    CompleteUserModel,
    GroupAttachmentResults,
    GroupListModel,
    GroupModel,
    IdPModel,
    IdPsListModel,
    OrganizationModel,
    UserListModel,
)
from api.broker_app.helpers import create_organization_action_payload
from api.identity.management_api import backend_client
from api.routers.organizations import helpers as organizations_helpers
from api.routers.organizations.helpers import (
    ListIdPsSortFilterChecker,
    ListUsersFromOrganizationSortFieldChecker,
)
from api.utils.helpers import mount_users_list


@pytest.fixture
def get_user_by_id_response_data() -> (
    dict[str, str | bool | list[str | dict[str, str]] | int | dict[str, bool | list[str]]]
):
    """Return a dummy user data."""
    return {
        "id": "dc60a026-631a-49f9-a837-45d6287f252f",
        "createdTimestamp": 1650910244544,
        "username": "dummy-user",
        "enabled": True,
        "totp": False,
        "emailVerified": True,
        "firstName": "Dummy",
        "lastName": "User",
        "email": "dummy.user@omnivector.solutions",
        "attributes": {
            "dummy": ["dummy"],
        },
        "disableableCredentialTypes": [],
        "requiredActions": [],
        "federatedIdentities": [
            {"identityProvider": "google", "userName": "dummy.user@omnivector.solutions"}
        ],
        "notBefore": 0,
        "access": {
            "manageGroupMembership": True,
            "view": True,
            "mapRoles": True,
            "impersonate": False,
            "manage": True,
        },
    }


@pytest.mark.asyncio
@mock.patch("api.routers.organizations.unpack_organization_id_from_token")
async def test_update_organization__check_http_400(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test if the endpoint returns 400 when there's no organization id in the token."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("No organization id in token")

    dummy_payload = {"display_name": "dummy-display-name"}

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch("/admin/management/organizations", json=dummy_payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_organization__check_http_200__update_display_name(
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 200 when updating only the display name."""
    new_display_name = "new-display-name"
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "domains": [{"name": "dummy-domain.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
            "display_name": ["dummy-organization"],
        },
    }
    update_organization_payload = organization_keycloak_payload.copy()
    update_organization_payload["attributes"]["display_name"] = new_display_name

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(f"/admin/realms/vantage/organizations/{organization_id}").mock(return_value=Response(204))

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch(
        "/admin/management/organizations", json={"display_name": new_display_name}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "id": organization_id,
        "name": "dummy-organization",
        "display_name": new_display_name,
        "url": "",
        "domains": ["dummy-domain.com"],
        "attributes": {
            "created_at": "2024-04-15T00:00:00",
            "logo": "https://www.dummy-logo.com",
            "owner": None,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_organization__check_http_200__update_logo(
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 200 when updating only the logo."""
    new_logo = "https://www.new-dummy-logo.com"
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "domains": [{"name": "dummy-domain.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }
    update_organization_payload = organization_keycloak_payload.copy()
    update_organization_payload["attributes"]["logo"] = [new_logo]

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(f"/admin/realms/vantage/organizations/{organization_id}").mock(return_value=Response(204))

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch("/admin/management/organizations", json={"logo": new_logo})
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "id": organization_id,
        "name": "dummy-organization",
        "display_name": "dummy-organization",
        "url": "",
        "domains": ["dummy-domain.com"],
        "attributes": {
            "created_at": "2024-04-15T00:00:00",
            "logo": new_logo,
            "owner": None,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_organization__check_http_200__update_domain__no_domain_set(
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 200 when updating only the domain.

    This test verifies if the domain is set when the organization doesn't have a domain set.
    """
    domain = str(uuid.uuid4())
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "redirectUrl": "",
        "domains": [],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
            'display_name': ['dummy-organization'],
        },
    }
    update_organization_payload = organization_keycloak_payload.copy()
    update_organization_payload["domains"] = [{"name": domain}]
    update_organization_payload.pop("realm")
    update_organization_payload["redirectUrl"] = ""

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(
        f"/admin/realms/vantage/organizations/{organization_id}",
        json=update_organization_payload
    ).mock(
        return_value=Response(204)
    )

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch("/admin/management/organizations", json={"domain": domain})
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "id": organization_id,
        "name": "dummy-organization",
        "display_name": "dummy-organization",
        "url": "",
        "domains": [domain],
        "attributes": {
            "created_at": "2024-04-15T00:00:00",
            "logo": "https://www.dummy-logo.com",
            "owner": None,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize("new_domain", [None, str(uuid.uuid4()), ""])
async def test_update_organization__check_http_200__update_domain__override_existing_domain(
    new_domain: str,
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 200 when updating only the domain.

    This test verifies if the domain passed in the request overrides the existing domain.
    """
    random_domain = str(uuid.uuid4())
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "redirectUrl": "",
        "domains": [{"name": random_domain}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
            'display_name': ['dummy-organization'],
        },
    }

    update_organization_payload = organization_keycloak_payload.copy()
    if new_domain is not None and new_domain != "":
        update_organization_payload["domains"] = [{"name": new_domain}]
    update_organization_payload.pop("realm")
    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(
        f"/admin/realms/vantage/organizations/{organization_id}",
        json=update_organization_payload
    ).mock(
        return_value=Response(204)
    )

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch("/admin/management/organizations", json={"domain": new_domain})
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "id": organization_id,
        "name": "dummy-organization",
        "display_name": "dummy-organization",
        "url": "",
        "domains": [random_domain] if new_domain is None or new_domain == "" else [new_domain],
        "attributes": {
            "created_at": "2024-04-15T00:00:00",
            "logo": "https://www.dummy-logo.com",
            "owner": None,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_organization__check_http_200__update_logo_and_display_name(
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 200 when updating both the logo and the display name."""
    new_logo = "https://www.new-dummy-logo.com"
    new_display_name = "new-display-name"
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "domains": [{"name": "dummy-domain.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
            'display_name': ['dummy-organization']
        },
    }
    update_organization_payload = organization_keycloak_payload.copy()
    update_organization_payload["name"] = new_display_name
    update_organization_payload["attributes"]["logo"] = [new_logo]

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(f"/admin/realms/vantage/organizations/{organization_id}").mock(return_value=Response(204))

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch(
        "/admin/management/organizations", json={"logo": new_logo, "display_name": new_display_name}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "id": organization_id,
        "name": "dummy-organization",
        "display_name": new_display_name,
        "url": "",
        "domains": ["dummy-domain.com"],
        "attributes": {
            "created_at": "2024-04-15T00:00:00",
            "logo": new_logo,
            "owner": None,
        },
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_organization__check_http_500(
    test_client: AsyncClient,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    organization_id: str,
):
    """Test if the endpoint returns 500 when there's an unknown error related to Keycloak."""
    new_logo = "https://www.new-dummy-logo.com"
    new_display_name = "new-display-name"
    organization_keycloak_payload = {
        "id": organization_id,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "domains": [{"name": "dummy-domain.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }
    update_organization_payload = organization_keycloak_payload.copy()
    update_organization_payload["displayName"] = new_display_name
    update_organization_payload["attributes"]["logo"] = [new_logo]

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(200, json=organization_keycloak_payload)
    )
    respx_mock.put(f"/admin/realms/vantage/organizations/{organization_id}").mock(
        return_value=Response(500, json={"error": "dummy error"})
    )

    inject_security_header("me", "admin:organizations:update")
    response = await test_client.patch(
        "/admin/management/organizations", json={"logo": new_logo, "display_name": new_display_name}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response_data == {"error": "dummy error", "message": "Contact support"}


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.helpers")
async def test_check_existing_organization_by_name__org_exists(
    mocked_helpers: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the expected response when the organization exists."""
    dummy_org_name = "dummy-org-name"

    mocked_helpers.is_organization_name_available = mock.AsyncMock(return_value=False)

    inject_security_header("me")
    response = await test_client.get(
        f"/admin/management/organizations/check-existing/{dummy_org_name}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"available": False}
    mocked_helpers.is_organization_name_available.assert_awaited_once_with(dummy_org_name)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.helpers")
async def test_check_existing_organization_by_name__org_doesnt_exist(
    mocked_helpers: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the expected response when the organization doesn't exist."""
    dummy_org_name = "dummy-org-name"

    mocked_helpers.is_organization_name_available = mock.AsyncMock(return_value=True)

    inject_security_header("me")
    response = await test_client.get(
        f"/admin/management/organizations/check-existing/{dummy_org_name}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"available": True}
    mocked_helpers.is_organization_name_available.assert_awaited_once_with(dummy_org_name)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "input_user_list, output_user_list",
    [
        ([], []),
        (["user@example.com"], ["user@example.com"]),
        (
            ["user1@example.com", "user2@example.com", "user3@example.com"],
            ["user1@example.com", "user2@example.com", "user3@example.com"],
        ),
        (
            ["user1@example.com", "user2@example.com", "user3@example.com"],
            ["user1@example.com", "user2@example.com"],
        ),
        (["user@example.com", "user@example.com", "user@example.com"], ["user@example.com"]),
    ],
)
async def test_check_existing_users(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    input_user_list: list[str],
    output_user_list: list[str],
    sample_uuid: str,
):
    """Test if the endoint returns the expected list of existing users."""
    unique_user_set = set(input_user_list)

    for user in unique_user_set:
        respx_mock.get(
            f"/admin/realms/vantage/organizations/{sample_uuid}/members",
            params={"search": user}
        ).mock(
            return_value=Response(200, json=[{"email": user}] if user in output_user_list else [])
        )

    inject_security_header("me", "admin:users:read")
    response = await test_client.post(
        "/admin/management/organizations/members/check-existing", json=input_user_list
    )

    assert response.status_code == status.HTTP_200_OK
    assert sorted(response.json()) == sorted(
        output_user_list
    )  # we sort because of the async nature of the endpoint


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_organization__check_error_when_cannot_check_current_user_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endoint returns 500 in case there's error checking the user's organizaiton."""
    sub = "me"
    name = "dummy-organization"
    display_name = "dummy-organization"
    error_message = "Something happened"

    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_organization__check_when_user_already_belong_to_an_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endoint returns 400 when the user already belong to an organization."""
    sub = "me"
    name = "dummy-organization"
    display_name = "dummy-organization"

    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(
            200, json=["dummy list to simulate the case where the user already have an organization"]
        )
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("number_of_members", [1, 1_000, 1_000_000, 1_000_000_000, 20_000])
@pytest.mark.asyncio
@mock.patch("api.routers.organizations.fetch_users_count", new_callable=mock.AsyncMock)
async def test_count_members_of_organization(
    mocked_fetch_users_count: mock.AsyncMock,
    number_of_members: int,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if counting members of an organization returns the expected number."""
    mocked_fetch_users_count.return_value = number_of_members

    inject_security_header("me", "admin:organizations:view")
    response = await test_client.get("/admin/management/organizations/members/count")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == number_of_members
    mocked_fetch_users_count.assert_awaited_once_with(sample_uuid)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_organization__check_when_input_name_is_already_in_use(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 409 when the input name is already in use."""
    sub = "me"
    name = "dummy-organization"
    display_name = "dummy-organization"

    respx_mock.get(
        f"/admin/realms/vantage/organizations/members/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[])
    )
    respx_mock.post(
        "/admin/realms/vantage/organizations"
    ).mock(
        return_value=Response(409, json={})
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name}
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"message": "Organization name already in use.", "error": None}


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_organization__check_internal_error_when_creating_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 500 when there's an error creating the organization."""
    sub = "me"
    name = "dummy-organization"
    display_name = "dummy-organization"
    error_message = "Something happened"

    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(
            200,
            json=[],
        )
    )

    respx_mock.get(
        f"/admin/realms/vantage/users/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[])
    )
    respx_mock.post(
        "/admin/realms/vantage/organizations"
    ).mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_create_organization__check_when_organization_is_created_successfully(
    mocked_organization_helpers: mock.Mock,
    mocked_rabbitmq_manager: mock.Mock,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the expected response when the organization is created successfully."""
    sub = "me"
    name = "dummy-organization"
    parsed_name = organizations_helpers.parse_org_name(name)
    display_name = "dummy-organization"
    logo = "https://www.dummy-logo.com"
    org_id = "dummy-id"
    org_admin_user_id = "AAAAA"
    service_account_admin_ops_user_id = "BBBBB"

    respx_mock.get(f"/admin/realms/vantage/organizations/{org_id}/members").mock(
        return_value=Response(
            200,
            json=[
                {"id": org_admin_user_id, "username": f"org-admin-{org_id}"},
                {"id": service_account_admin_ops_user_id, "username": "service-account-admin-ops"},
            ],
        )
    )
    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(
            200,
            json=[],
        )
    )
    respx_mock.get(f"/admin/realms/vantage/users/{sub}/orgs").mock(return_value=Response(200, json=[]))
    respx_mock.post("/admin/realms/vantage/organizations").mock(return_value=Response(201, json={}))
    respx_mock.get(
        "/admin/realms/vantage/organizations",
        params={"search": parsed_name, "max": 1, "first": 0}).mock(
        return_value=Response(200, json=[{"id": org_id}])
    )
    respx_mock.delete(f"/admin/realms/vantage/users/{org_admin_user_id}").mock(return_value=Response(204))
    respx_mock.delete(f"/admin/realms/vantage/organizations/{org_id}/members/{service_account_admin_ops_user_id}").mock(
        return_value=Response(204)
    )

    mocked_rabbitmq_manager.call = mock.AsyncMock()
    mocked_rabbitmq_manager.call.return_value = True

    mocked_organization_helpers.add_admin_user_and_set_up_permissions = mock.AsyncMock()
    mocked_organization_helpers.parse_org_name = mock.Mock(return_value=parsed_name)

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name, "logo": logo}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "id": org_id,
        "name": name,
        "display_name": display_name,
        "url": str(),
        "domains": [],
        "attributes": {
            "created_at": "2023-05-10T00:00:00+00:00",
            "logo": logo,
            "owner": sub,
        },
    }

    message_body = create_organization_action_payload(org_id)
    mocked_rabbitmq_manager.call.assert_awaited_once_with(message_body)
    mocked_organization_helpers.add_admin_user_and_set_up_permissions.assert_awaited_once_with(sub, org_id)
    mocked_organization_helpers.parse_org_name.assert_called_once_with(name)


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_create_organization__check_internal_error_setting_up_admin_user(
    mocked_organization_helpers: mock.Mock,
    mocked_rabbitmq_manager: mock.Mock,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 500 when there's an error setting up the admin user."""
    sub = "me"
    name = "dummy-organization"
    parsed_name = organizations_helpers.parse_org_name(name)
    display_name = "dummy-organization"
    logo = "https://www.dummy-logo.com"
    org_id = "dummy-id"
    org_admin_user_id = "AAAAA"
    service_account_admin_ops_user_id = "BBBBB"

    respx_mock.get(f"/admin/realms/vantage/organizations/{org_id}/members").mock(
        return_value=Response(
            200,
            json=[
                {"id": org_admin_user_id, "username": f"org-admin-{org_id}"},
                {"id": service_account_admin_ops_user_id, "username": "service-account-admin-ops"},
            ],
        )
    )
    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(
            200,
            json=[],
        )
    )
    respx_mock.get(
        f"/admin/realms/vantage/users/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[])
    )
    respx_mock.post(
        "/admin/realms/vantage/organizations"
    ).mock(
        return_value=Response(201, json={})
    )
    respx_mock.get(
        "/admin/realms/vantage/organizations",
        params={"search": parsed_name, "max": 1, "first": 0}
    ).mock(
        return_value=Response(200, json=[{"id": org_id}])
    )
    respx_mock.delete(f"/admin/realms/vantage/users/{org_admin_user_id}").mock(return_value=Response(204))
    respx_mock.delete(f"/admin/realms/vantage/organizations/{org_id}/members/{service_account_admin_ops_user_id}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/organizations/{org_id}").mock(return_value=Response(204))

    mocked_rabbitmq_manager.call = mock.AsyncMock()
    mocked_rabbitmq_manager.call.return_value = True

    mocked_organization_helpers.add_admin_user_and_set_up_permissions = mock.AsyncMock()
    mocked_organization_helpers.add_admin_user_and_set_up_permissions.side_effect = Exception("Error")
    mocked_organization_helpers.parse_org_name = mock.Mock(return_value=parsed_name)

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name, "logo": logo}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    mocked_rabbitmq_manager.call.assert_not_awaited()
    mocked_organization_helpers.add_admin_user_and_set_up_permissions.assert_awaited_once_with(sub, org_id)
    mocked_organization_helpers.parse_org_name.assert_called_once_with(name)


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_create_organization__check_when_theres_error_to_publish_rabbitmq_message(
    mocked_organization_helpers: mock.Mock,
    mocked_rabbitmq_manager: mock.Mock,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 500 when there's an error to publish the RabbitMQ message."""
    sub = "me"
    name = "dummy-organization"
    parsed_name = organizations_helpers.parse_org_name(name)
    display_name = "dummy-organization"
    logo = "https://www.dummy-logo.com"
    org_id = "dummy-id"
    org_admin_user_id = "AAAAA"
    service_account_admin_ops_user_id = "BBBBB"

    respx_mock.get(f"/admin/realms/vantage/organizations/{org_id}/members").mock(
        return_value=Response(
            200,
            json=[
                {"id": org_admin_user_id, "username": f"org-admin-{org_id}"},
                {"id": service_account_admin_ops_user_id, "username": "service-account-admin-ops"},
            ],
        )
    )
    respx_mock.get(
        f"/admin/realms/vantage/organizations/members/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[])
    )
    respx_mock.post(
        "/admin/realms/vantage/organizations"
    ).mock(
        return_value=Response(201, json={})
    )
    respx_mock.get(
        "/admin/realms/vantage/organizations",
        params={"search": parsed_name, "max": 1, "first": 0}
    ).mock(
        return_value=Response(200, json=[{"id": org_id}])
    )
    respx_mock.delete(f"/admin/realms/vantage/users/{org_admin_user_id}").mock(return_value=Response(204))
    respx_mock.delete(f"/admin/realms/vantage/organizations/{org_id}/members/{service_account_admin_ops_user_id}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/organizations/{org_id}").mock(return_value=Response(204))

    mocked_rabbitmq_manager.call = mock.AsyncMock()
    mocked_rabbitmq_manager.call.return_value = None
    mocked_rabbitmq_manager.call.side_effect = Exception("Error sending RabbitMQ message")

    mocked_organization_helpers.add_admin_user_and_set_up_permissions = mock.AsyncMock(return_value=None)
    mocked_organization_helpers.parse_org_name = mock.Mock(return_value=parsed_name)

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.post(
        "/admin/management/organizations", json={"name": name, "display_name": display_name, "logo": logo}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["message"] == "Error sending RabbitMQ message"

    message_body = create_organization_action_payload(org_id)
    mocked_rabbitmq_manager.call.assert_awaited_once_with(message_body)
    mocked_organization_helpers.add_admin_user_and_set_up_permissions.assert_awaited_once_with(sub, org_id)
    mocked_organization_helpers.parse_org_name.assert_called_once_with(name)


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_organization__check_when_user_belongs_to_an_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the expected response when user belong to an organization."""
    organization = {
        "id": "123456789",
        "alias": "omnivector",
        "name": "Omnivector Solutions",
        "redirectUrl": "",
        "domains": [],
        "attributes": {
            "created_at": [datetime.now().isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }
    sub = "me"

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(200))
    respx_mock.get(
        f"/admin/realms/vantage/organizations/members/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[organization])
    )
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{organization['id']}"
    ).mock(
        return_value=Response(200, json=organization)
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.get("/admin/management/organizations/my")

    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == [
        json.loads(
            OrganizationModel(
                id=organization.get("id"),
                name=organization.get("alias"),
                display_name=organization.get("name"),
                url=organization.get("redirectUrl"),
                domains=organization.get("domains"),
                attributes={
                    "created_at": "2023-05-10T00:00:00",
                    "logo": "https://www.dummy-logo.com",
                },
            ).json()
        )
    ]


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_organization__check_internal_error(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 500 when an unexpected error happens."""
    sub = "me"
    error_message = "Something happened"

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(200))
    respx_mock.get(f"/admin/realms/vantage/organizations/members/{sub}/organizations").mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.get("/admin/management/organizations/my")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@freeze_time("2023-05-10")
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_organization__check_when_user_doesnt_belong_to_an_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when the user doesn't belong to any organization."""
    sub = "me"

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(200))
    respx_mock.get(
        f"/admin/realms/vantage/organizations/members/{sub}/organizations"
    ).mock(
        return_value=Response(200, json=[])
    )

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.get("/admin/management/organizations/my")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_organization__check_when_user_doesnt_exist(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 428 when the user doesn't exist."""
    sub = "me"

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(404))

    inject_security_header(sub, "admin:organizations:view")
    response = await test_client.get("/admin/management/organizations/my")

    assert response.status_code == status.HTTP_428_PRECONDITION_REQUIRED
    assert response.json()["message"] == "User not found"


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_from_organization(
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns the expected response."""
    page = 0
    per_page = 100
    search = "whatever"

    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"first": page, "max": per_page, "search": search},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:users:read")
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={"search": search, "after": page, "per_page": per_page},
    )

    users_list = mount_users_list(dummy_user_list)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == users_list.dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_from_organization__check_search_input(
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint is searchable by the query parameter `input`."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"first": page, "max": per_page, "search": "foo@boo.com"},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:users:read")
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={"after": page, "per_page": per_page, "search": "foo@boo.com"},
    )

    users_list = mount_users_list(dummy_user_list)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == users_list.dict()


@pytest.mark.parametrize("sort_field", ListUsersFromOrganizationSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_from_organization__check_sorting_over_user_fields(
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sort_field: str,
    sample_uuid: str,
):
    """Test if the endpoint is sortable by the expected fields."""
    page = 0
    per_page = 100
    search = "whatever"

    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"first": page, "max": per_page, "search": search},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:users:read")

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    user_list_model = mount_users_list(dummy_user_list)

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users,
        key=lambda user: getattr(user, sort_field) or "",
        reverse=not sort_ascending,
    )
    assert response.json() == UserListModel(users=sorted_users).dict()

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users,
        key=lambda user: getattr(user, sort_field) or "",
        reverse=not sort_ascending,
    )
    assert response.json() == UserListModel(users=sorted_users).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_from_organization__check_sorting_over_user_fields_without_name(
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns the expected response when the user doesn't have a name."""
    page = 0
    per_page = 100
    search = "whatever"
    sort_field = "name"

    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"first": page, "max": per_page, "search": search},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:users:read")

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    user_list_model = mount_users_list(dummy_user_list)

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users,
        key=lambda user: getattr(user, sort_field) or "",
        reverse=not sort_ascending,
    )
    assert response.json()["users"][0]["name"] is None
    assert response.json()["users"][-1]["name"] is not None
    assert response.json() == UserListModel(users=sorted_users).dict()

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/organizations/members",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users,
        key=lambda user: getattr(user, sort_field) or "",
        reverse=not sort_ascending,
    )
    assert response.json()["users"][0]["name"] is not None
    assert response.json()["users"][-1]["name"] is None
    assert response.json() == UserListModel(users=sorted_users).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_by_id__check_route_payload_when_user_exists(
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns the expected response when the user exists."""
    user = dummy_user_list[0]

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user.get('id')}").mock(
        return_value=Response(200)
    )
    respx_mock.get(f"/admin/realms/vantage/users/{user.get('id')}").mock(
        return_value=Response(200, json=user)
    )

    inject_security_header("me", "admin:users:read")
    response = await test_client.get(f"/admin/management/organizations/members/{user.get('id')}")

    user = CompleteUserModel(**user)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == user.dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_user_by_id__check_route_payload_when_user_doesnt_exist(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the user doesn't exist."""
    user_id = "dummy-user-id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(404))

    inject_security_header("me", "admin:users:read")
    response = await test_client.get(f"/admin/management/organizations/members/{user_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_by_id__check_route_return_when_user_exists(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 204 when the user exists."""
    user_id = "dummy-user-id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.delete(f"/admin/realms/vantage/users/{user_id}").mock(return_value=Response(204))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(f"/admin/management/organizations/members/{user_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_by_id__check_internal_error(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 500 when there's an error deleting the user."""
    user_id = "dummy-user-id"
    error_message = "Something happened"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.delete(f"/admin/realms/vantage/users/{user_id}").mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(f"/admin/management/organizations/members/{user_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_by_id__check_route_return_when_user_doesnt_exist(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 404 when the user doesn't exist."""
    user_id = "dummy-user-id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(400))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(f"/admin/management/organizations/members/{user_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups_from_user__check_route_return_when_user_exists__empty_group_list(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the user exists but has no groups."""
    user_id = "dummy-user-id"
    page = 0
    per_page = 100

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.get(
        f"/admin/realms/vantage/users/{user_id}/groups",
        params={"first": page, "max": per_page, "briefRepresentation": False},
    ).mock(return_value=Response(200, json=[]))

    inject_security_header(user_id, "admin:users:read", "admin:groups:view")
    response = await test_client.get(
        f"/admin/management/organizations/members/{user_id}/groups",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupListModel(groups=[]).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups_from_user__check_route_return_when_user_exists__no_empty_group_list(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the user exists and has groups."""
    user_id = "dummy-user-id"
    page = 0
    per_page = 100

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.get(
        f"/admin/realms/vantage/users/{user_id}/groups",
        params={"first": page, "max": per_page, "briefRepresentation": False},
    ).mock(return_value=Response(200, json=[group_example]))

    inject_security_header(user_id, "admin:users:read", "admin:groups:view")
    response = await test_client.get(
        f"/admin/management/organizations/members/{user_id}/groups",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == GroupListModel(
            groups=[GroupModel(**group_example, roles=group_example.get("clientRoles").get("default"))]
        ).dict()
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups_from_user__check_route_return_when_user_doesnt_exist(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the user doesn't exist."""
    user_id = "dummy-user-id"
    page = 0
    per_page = 100

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(404))

    inject_security_header(user_id, "admin:users:read", "admin:groups:view")
    response = await test_client.get(
        f"/admin/management/organizations/members/{user_id}/groups",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups_from_user__check_forbidden_access_when_fetching_another_user_roles_with_no_permissions(  # noqa: E501
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 403 when the user tries to fetch another user's groups without permissions."""  # noqa: E501
    user_id = "dummy-user-id"
    page = 0
    per_page = 100

    respx_mock.get(
        f"/users/{user_id}/groups",
        params={"first": page, "max": per_page, "briefRepresentation": False},
    ).mock(return_value=Response(200, json=[group_example]))

    inject_security_header("me")
    response = await test_client.get(
        f"/admin/management/organizations/members/{user_id}/groups",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert {"detail": "Forbidden"} == response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_idp__check_success(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 204 when the IDP is successfully deleted."""
    respx_mock.delete(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers/{sample_uuid}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/identity-providers/instances/{sample_uuid}").mock(
        return_value=Response(204)
    )

    inject_security_header("me", "admin:idps:delete")
    response = await test_client.delete("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_idp__check_idp_not_found(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 404 when the IDP is not found."""
    respx_mock.delete(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers/{sample_uuid}").mock(
        return_value=Response(404)
    )
    respx_mock.delete(f"/admin/realms/vantage/identity-providers/instances/{sample_uuid}").mock(
        return_value=Response(404)
    )

    inject_security_header("me", "admin:idps:delete")
    response = await test_client.delete("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_idp__check_internal_error(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 500 when the IDP is not successfully deleted."""
    error_message = "Something happened"
    respx_mock.delete(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers/{sample_uuid}").mock(
        return_value=Response(204)
    )
    respx_mock.delete(f"/admin/realms/vantage/identity-providers/instances/{sample_uuid}").mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header("me", "admin:idps:delete")
    response = await test_client.delete("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.parametrize("idp_name", [("azure"), ("google"), ("github")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_idp__check_when_idp_is_supported(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
):
    """Test if the endpoint returns 201 when the IDP is successfully created."""
    keycloak_organization_payload = {
        "id": sample_uuid,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "redirectUrl": "",
        "domains": [{"name": "dummy-organization.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }

    idp_attrs = {
        "client_id": "dummy-client-id",
        "client_secret": "dummy-client-secret",
    }
    if idp_name == "azure":
        idp_attrs["app_identifier"] = "dummy-app-identifier"

    config_generator = getattr(organizations_helpers, f"generate_{idp_name}_config")

    idp_config = config_generator(organization_id=sample_uuid, **idp_attrs)

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}").mock(
        return_value=Response(200, json=keycloak_organization_payload)
    )
    respx_mock.post(
        "/admin/realms/vantage/identity-provider/instances",
        json=idp_config
    ).mock(
        return_value=Response(201)
    )
    respx_mock.post(
        f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers",
        content=sample_uuid
    ).mock(
        return_value=Response(204)
    )

    inject_security_header("me", "admin:idps:create")
    response = await test_client.post(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **idp_attrs}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert "message" in response.json()


@pytest.mark.parametrize("idp_name", [("azure"), ("google"), ("github")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_idp__check_when_organization_already_have_an_idp(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
):
    """Test if the endpoint returns 409 when the organization already have an IDP."""
    keycloak_organization_payload = {
        "id": sample_uuid,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "redurectUrl": "",
        "domains": [{"name": "dummy-organization.com"}],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }

    idp_attrs = {
        "client_id": "dummy-client-id",
        "client_secret": "dummy-client-secret",
    }
    if idp_name == "azure":
        idp_attrs["app_identifier"] = "dummy-app-identifier"

    config_generator = getattr(organizations_helpers, f"generate_{idp_name}_config")

    idp_config = config_generator(organization_id=sample_uuid, **idp_attrs)

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}").mock(
        return_value=Response(200, json=keycloak_organization_payload)
    )
    respx_mock.post(
        "/admin/realms/vantage/identity-provider/instances",
        json=idp_config
    ).mock(
        return_value=Response(409)
    )

    inject_security_header("me", "admin:idps:create")
    response = await test_client.post(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **idp_attrs}
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "message" in response.json()


@pytest.mark.parametrize("idp_name", [("azure"), ("google"), ("github")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_idp__check_when_organization_has_no_domain(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
):
    """Test if the endpoint returns 400 when the organization has no domain set up."""
    keycloak_organization_payload = {
        "id": sample_uuid,
        "alias": "dummy-organization",
        "name": "dummy-organization",
        "realm": "vantage",
        "redirectUrl": "",
        "domains": [],
        "attributes": {
            "created_at": [datetime(2024, 4, 15).isoformat()],
            "logo": ["https://www.dummy-logo.com"],
        },
    }

    idp_attrs = {
        "client_id": "dummy-client-id",
        "client_secret": "dummy-client-secret",
    }
    if idp_name == "azure":
        idp_attrs["app_identifier"] = "dummy-app-identifier"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}").mock(
        return_value=Response(200, json=keycloak_organization_payload)
    )

    inject_security_header("me", "admin:idps:create")
    response = await test_client.post(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **idp_attrs}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "message" in response.json()


@pytest.mark.parametrize("idp_name", [("random_string"), ("random_idp"), ("not-supported")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_create_idp__check_when_idp_is_not_supported(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
):
    """Test if the endpoint returns 422 when the IDP is not supported."""
    idp_attrs = {
        "client_id": "dummy-client-id",
        "client_secret": "dummy-client-secret",
    }

    inject_security_header("me", "admin:idps:create")
    response = await test_client.post(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **idp_attrs}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "idp_name,body",
    [
        (
            "azure",
            {
                "client_id": "dummy-client-id",
                "client_secret": "dummy-client-secret",
                "app_identifier": "dummy-app-identifier",
            },
        ),
        # ("azure", {"client_secret": "dummy-client-secret", "app_identifier": "dummy-app-identifier"}),
        # ("azure", {"client_id": "dummy-client-id", "app_identifier": "dummy-app-identifier"}),
        # ("azure", {"client_id": "dummy-client-id"}),
        # ("azure", {"client_secret": "dummy-client-secret"}),
        # ("azure", {"app_identifier": "dummy-app-identifier"}),
        # ("azure", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        # ("google", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        # ("google", {"client_secret": "dummy-client-secret"}),
        # ("google", {"client_id": "dummy-client-id"}),
        # ("github", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        # ("github", {"client_secret": "dummy-client-secret"}),
        # ("github", {"client_id": "dummy-client-id"}),
    ],
)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_idp__check_when_idp_is_successfully_patched(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
    body: Dict[str, str],
):
    """Test if the endpoint returns 200 when the IDP is successfully patched."""
    idp_update_body = {"config": {}, "providerId": idp_name}

    if body.get("client_id") is not None:
        idp_update_body["config"]["clientId"] = body.get("client_id")
    if body.get("client_secret") is not None:
        idp_update_body["config"]["clientSecret"] = body.get("client_secret")
    if idp_name == "azure" and body.get("app_identifier") is not None:
        idp_update_body["config"][
            "tokenUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "jwksUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "issuer"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/v2.0"
        idp_update_body["config"][
            "authorizationUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/authorize"
        idp_update_body["config"][
            "logoutUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/logout"
        idp_update_body["providerId"] = "oidc"

    respx_mock.put(
        f"/admin/realms/vantage/identity-provider/instances/{sample_uuid}",
        json=idp_update_body
    ).mock(
        return_value=Response(204)
    )

    inject_security_header("me", "admin:idps:update")
    response = await test_client.patch(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **body}
    )

    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()


@pytest.mark.parametrize(
    "idp_name,body",
    [
        (
            "azure",
            {
                "client_id": "dummy-client-id",
                "client_secret": "dummy-client-secret",
                "app_identifier": "dummy-app-identifier",
            },
        ),
        ("azure", {"client_secret": "dummy-client-secret", "app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id", "app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id"}),
        ("azure", {"client_secret": "dummy-client-secret"}),
        ("azure", {"app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("google", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("google", {"client_secret": "dummy-client-secret"}),
        ("google", {"client_id": "dummy-client-id"}),
        ("github", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("github", {"client_secret": "dummy-client-secret"}),
        ("github", {"client_id": "dummy-client-id"}),
    ],
)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_idp__check_when_organization_doesnt_have_an_idp(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
    body: Dict[str, str],
):
    """Test if the endpoint returns 404 when the organization doesn't have an IDP."""
    idp_update_body = {"config": {}, "providerId": idp_name}

    if body.get("client_id") is not None:
        idp_update_body["config"]["clientId"] = body.get("client_id")
    if body.get("client_secret") is not None:
        idp_update_body["config"]["clientSecret"] = body.get("client_secret")
    if idp_name == "azure" and body.get("app_identifier") is not None:
        idp_update_body["config"][
            "tokenUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "jwksUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "issuer"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/v2.0"
        idp_update_body["config"][
            "authorizationUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/authorize"
        idp_update_body["config"][
            "logoutUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/logout"
        idp_update_body["providerId"] = "oidc"

    respx_mock.put(
        f"/admin/realms/vantage/identity-provider/instances/{sample_uuid}",
        json=idp_update_body
    ).mock(
        return_value=Response(404)
    )

    inject_security_header("me", "admin:idps:update")
    response = await test_client.patch(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **body}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.parametrize(
    "idp_name,body",
    [
        (
            "azure",
            {
                "client_id": "dummy-client-id",
                "client_secret": "dummy-client-secret",
                "app_identifier": "dummy-app-identifier",
            },
        ),
        ("azure", {"client_secret": "dummy-client-secret", "app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id", "app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id"}),
        ("azure", {"client_secret": "dummy-client-secret"}),
        ("azure", {"app_identifier": "dummy-app-identifier"}),
        ("azure", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("google", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("google", {"client_secret": "dummy-client-secret"}),
        ("google", {"client_id": "dummy-client-id"}),
        ("github", {"client_id": "dummy-client-id", "client_secret": "dummy-client-secret"}),
        ("github", {"client_secret": "dummy-client-secret"}),
        ("github", {"client_id": "dummy-client-id"}),
    ],
)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_idp__check_internal_error(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    idp_name: str,
    body: Dict[str, str],
):
    """Test if the endpoint returns 500 when an internal error happens."""
    error_message = "Something happened"
    idp_update_body = {"config": {}, "providerId": idp_name}

    if body.get("client_id") is not None:
        idp_update_body["config"]["clientId"] = body.get("client_id")
    if body.get("client_secret") is not None:
        idp_update_body["config"]["clientSecret"] = body.get("client_secret")
    if idp_name == "azure" and body.get("app_identifier") is not None:
        idp_update_body["config"][
            "tokenUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "jwksUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/token"
        idp_update_body["config"][
            "issuer"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/v2.0"
        idp_update_body["config"][
            "authorizationUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/authorize"
        idp_update_body["config"][
            "logoutUrl"
        ] = f"https://login.microsoftonline.com/${body.get('app_identifier')}/oauth2/v2.0/logout"
        idp_update_body["providerId"] = "oidc"

    respx_mock.put(
        f"/admin/realms/vantage/identity-provider/instances/{sample_uuid}",
        json=idp_update_body
    ).mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header("me", "admin:idps:update")
    response = await test_client.patch(
        "/admin/management/organizations/idps", json={"idp_name": idp_name, **body}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "message" in response.json()
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_idps__check_request_response_with_empty_idp_list(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 200 when an empty list of idps is fetched."""
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers"
    ).mock(
        return_value=Response(200, json=[])
    )

    inject_security_header("me", "admin:idps:read")
    response = await test_client.get("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == IdPsListModel(idps=[]).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_idps__check_internal_error(
    respx_mock: MockRouter, inject_security_header: Callable, test_client: AsyncClient, sample_uuid: str
):
    """Test if the endpoint returns 500 when an internal error happens."""
    error_message = "Something happened"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers").mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header("me", "admin:idps:read")
    response = await test_client.get("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_idps__check_request_response_with_no_empty_idp_list(
    idp_example: Dict[str, Union[Dict, str, bool]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the idps are successfully fetched."""
    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers").mock(
        return_value=Response(200, json=[idp_example])
    )

    inject_security_header("me", "admin:idps:read")
    response = await test_client.get("/admin/management/organizations/idps")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == IdPsListModel(idps=[IdPModel(**idp_example)]).dict()


@pytest.mark.parametrize("sort_field", ListIdPsSortFilterChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_idps__check_request_response_with_no_empty_idps_list__test_sorting(
    idp_example: Dict[str, Union[Dict, str, bool]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sort_field: str,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the idps are successfully fetched."""
    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/identity-providers").mock(
        return_value=Response(200, json=[idp_example])
    )

    inject_security_header("me", "admin:idps:read")

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/organizations/idps",
        params={"sort_field": sort_field, "sort_ascending": sort_ascending},
    )
    idps = sorted(
        [IdPModel(**idp_example)],
        key=lambda idp: getattr(idp, sort_field),
        reverse=not sort_ascending,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == IdPsListModel(idps=idps).dict()

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/organizations/idps",
        params={"sort_field": sort_field, "sort_ascending": sort_ascending},
    )
    idps = sorted(
        [IdPModel(**idp_example)],
        key=lambda idp: getattr(idp, sort_field),
        reverse=not sort_ascending,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == IdPsListModel(idps=idps).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_user_groups__check_if_its_possible_to_assign_existent_group_to_an_user(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the user is successfully assigned to a group."""
    user_id = "dummy-user-id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.put(
        f"/admin/realms/vantage/users/{user_id}/groups/{group_example.get('id')}",
    ).mock(return_value=Response(204))

    inject_security_header("me", "admin:users:update")
    response = await test_client.patch(
        f"/admin/management/organizations/members/{user_id}/groups",
        json={"groups": [group_example.get("id")]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupAttachmentResults(successes=[group_example.get("id")]).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_user_groups__check_if_its_possible_to_assign_multiple_existent_groups_to_an_user(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 200 when the user is successfully assigned to multiple groups."""
    user_id = "dummy-user-id"
    groups_to_assign = 5

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    for _ in range(groups_to_assign):
        respx_mock.put(
            f"/admin/realms/vantage/users/{user_id}/groups/{group_example.get('id')}",
        ).mock(return_value=Response(204))

    inject_security_header("me", "admin:users:update")
    response = await test_client.patch(
        f"/admin/management/organizations/members/{user_id}/groups",
        json={"groups": [group_example.get("id") for _ in range(groups_to_assign)]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == GroupAttachmentResults(successes=[group_example.get("id") for _ in range(groups_to_assign)]).dict()
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_patch_user_groups__check_route_return_when_user_doesnt_exist(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the user doesn't exist."""
    user_id = "dummy-user-id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(404))

    inject_security_header("me", "admin:users:update")
    response = await test_client.patch(
        f"/admin/management/organizations/members/{user_id}/groups",
        json={"groups": [group_example.get("id")]},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_group__check_successful_deletion(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 204 when the group is successfully deleted."""
    user_id = "dummy-user-id"
    group_id = group_example.get("id")

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.delete(
        f"/admin/realms/vantage/users/{user_id}/groups/{group_id}",
    ).mock(return_value=Response(204))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(
        f"/admin/management/organizations/members/{user_id}/groups/{group_id}"
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_groups__check_when_user_does_not_belong_to_organization(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the user doesn't belong to the organization."""
    user_id = "dummy-user-id"
    group_id = group_example.get("id")

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(404))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(
        f"/admin/management/organizations/members/{user_id}/groups/{group_id}"
    )
    response_json = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response_json.get("message") == "User not found."


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_groups__check_when_group_does_not_exist(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the group doesn't exist."""
    user_id = "dummy-user-id"
    group_id = group_example.get("id")

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(200))
    respx_mock.delete(
        f"/admin/realms/vantage/users/{user_id}/groups/{group_id}",
    ).mock(return_value=Response(404))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(
        f"/admin/management/organizations/members/{user_id}/groups/{group_id}"
    )
    response_json = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response_json.get("message") == "Group not found."


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_delete_user_groups__check_when_user_doesnt_belong_to_callers_organization(
    group_example: Dict[str, Union[str, Dict, List]],
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test if the endpoint returns 404 when the user doesn't belong to the caller's organization."""
    user_id = "dummy-user-id"
    dummy_org_id = "1a8bbd5f-de88-4e67-ba77-cb89dd021f06"

    assert dummy_org_id != sample_uuid

    respx_mock.get(f"/admin/realms/vantage/organizations/{sample_uuid}/members/{user_id}").mock(return_value=Response(404))

    inject_security_header("me", "admin:users:delete")
    response = await test_client.delete(
        f"/admin/management/organizations/members/{user_id}/groups/{group_example.get('id')}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        ([], []),
        ([], ["role"]),
        ([], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
async def test_create_invite__check_201__no_error_sending_email(
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: str,
    requester_organization: str,
    sample_uuid: str,
):
    """Test if the endpoint returns 201 when the invite request is successful."""
    user_representation = {
        "email": "test@omnivector.solutions",
        "username": "test@omnivector.solutions",
        "enabled": True,
        "groups": groups,
        "emailVerified": True,
        "clientRoles": {"default": roles},
        "attributes": {"created_at": [str(datetime.now())], "inviter": requester_email},
    }

    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    respx_mock.post("/admin/realms/vantage/users", json=user_representation).mock(return_value=Response(201))
    respx_mock.post(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members/invite-user",
        data={
            "email": "test@omnivector.solutions",
            "send": False,
            "inviterId": "me",
        },
    ).mock(return_value=Response(204))

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=False)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=False)

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_201_CREATED
    mocked_helpers.is_email_allocated_to_other_account.assert_awaited_once_with(email=input_body.get("email"))

    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)


@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        ([], []),
        ([], ["role"]),
        ([], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
async def test_create_invite__check_error_invite_request(
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: str,
    sample_uuid: str,
):
    """Test if the endpoint returns 500 when the invite request fails."""
    user_representation = {
        "email": "test@omnivector.solutions",
        "username": "test@omnivector.solutions",
        "enabled": True,
        "groups": groups,
        "emailVerified": True,
        "clientRoles": {"default": roles},
        "attributes": {"created_at": [str(datetime.now())], "inviter": requester_email},
    }
    error_message = "Error happened"

    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    respx_mock.post("/admin/realms/vantage/users", json=user_representation).mock(return_value=Response(201))
    respx_mock.post(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members/invite-user",
        data={
            "email": "test@omnivector.solutions",
            "send": False,
            "inviterId": "me",
        },
    ).mock(return_value=Response(500, json={"error": error_message}))

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=False)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=False)

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message
    mocked_helpers.is_email_allocated_to_other_account.assert_awaited_once_with(email=input_body.get("email"))
    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)

@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        ([], []),
        ([], ["role"]),
        ([], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
async def test_create_invite__check_when_input_email_is_already_in_use(
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: str,
    requester_organization: str,
    sample_uuid: str,
):
    """Test if the endpoint returns 201 when the input email is already in use but doesn't belong to any organization."""  # noqa: E501
    user_representation = {
        "email": "test@omnivector.solutions",
        "username": "test@omnivector.solutions",
        "enabled": True,
        "groups": groups,
        "emailVerified": True,
        "clientRoles": {"default": roles},
        "attributes": {"created_at": [str(datetime.now())], "inviter": requester_email},
    }

    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    respx_mock.post("/admin/realms/vantage/users", json=user_representation).mock(return_value=Response(409))
    respx_mock.post(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members/invite-user",
        data={
            "email": "test@omnivector.solutions",
            "send": False,
            "inviterId": "me",
        },
    ).mock(return_value=Response(204))

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=False)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=False)
    mocked_helpers.assign_group_to_user_by_group_name = mock.AsyncMock(return_value=None)
    mocked_helpers.update_inviter_id = mock.AsyncMock(return_value=None)

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_201_CREATED
    assert "message" in response.json()
    mocked_helpers.is_email_allocated_to_other_account.assert_awaited_once_with(email=input_body.get("email"))

    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)
    if len(groups) > 0:
        mocked_helpers.assign_group_to_user_by_group_name.assert_has_awaits(
            calls=[mock.call(email="test@omnivector.solutions", group_name=group) for group in groups],
            any_order=True,
        )
    else:
        mocked_helpers.assign_group_to_user_by_group_name.assert_not_awaited()

    mocked_helpers.update_inviter_id.assert_has_awaits(
        calls=[mock.call("test@omnivector.solutions", requester_email)],
    )

@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
async def test_create_invite__check_when_one_of_the_input_groups_doesnt_exist(
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: str,
    sample_uuid: str,
):
    """Test if the endpoint returns 400 when one of the input groups doesn't exist."""
    user_representation = {
        "email": "test@omnivector.solutions",
        "username": "test@omnivector.solutions",
        "enabled": True,
        "groups": groups,
        "emailVerified": True,
        "clientRoles": {"default": roles},
        "attributes": {"created_at": [str(datetime.now())], "inviter": requester_email},
    }

    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    respx_mock.post("/admin/realms/vantage/users", json=user_representation).mock(return_value=Response(500))
    respx_mock.post(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members/invite-user",
        data={
            "email": "test@omnivector.solutions",
            "send": False,
            "inviterId": "me",
        },
    ).mock(return_value=Response(204))

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=False)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=False)

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "message" in response.json()
    mocked_helpers.is_email_allocated_to_other_account.assert_awaited_once_with(email=input_body.get("email"))
    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)


@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
@mock.patch("api.routers.organizations.backend_client")
async def test_create_invite__check_when_user_cannot_be_invited(
    mocked_backend_client: mock.Mock,
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    test_client: AsyncClient,
    inject_security_header: Callable,
    sample_uuid: str,
):
    """Test if the endpoint returns 409 when the user cannot be invited."""
    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=True)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=False)
    mocked_backend_client.post = mock.AsyncMock()

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_409_CONFLICT
    mocked_helpers.is_email_allocated_to_other_account.assert_awaited_once_with(email=input_body.get("email"))
    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)
    mocked_backend_client.post.assert_not_awaited()


@freeze_time("2022-07-01 12:21:00", tz_offset=0)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "groups,roles",
    [
        (["group"], ["role"]),
        (["group1", "group2"], ["role"]),
        (["group"], ["role1", "role2"]),
        (["group1", "group2"], []),
        (["group"], []),
    ],
)
@mock.patch("api.routers.organizations.helpers")
@mock.patch("api.routers.organizations.backend_client")
async def test_create_invite__check_user_limit(
    mocked_backend_client: mock.Mock,
    mocked_helpers: mock.Mock,
    groups: List[str],
    roles: List[str],
    test_client: AsyncClient,
    inject_security_header: Callable,
    sample_uuid: str,
):
    """Test if the endpoint returns 403 when the organization has reached the limit of users."""
    input_body = {"email": "test@omnivector.solutions", "groups": groups, "roles": roles}

    mocked_helpers.is_email_allocated_to_other_account = mock.AsyncMock(return_value=True)
    mocked_helpers.has_organization_reached_user_limit = mock.AsyncMock(return_value=True)
    mocked_backend_client.post = mock.AsyncMock()

    inject_security_header("me", "admin:invites:create")
    response = await test_client.post("/admin/management/organizations/invites", json=input_body)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mocked_helpers.is_email_allocated_to_other_account.assert_not_awaited()
    mocked_helpers.has_organization_reached_user_limit.assert_awaited_once_with(sample_uuid)
    mocked_backend_client.post.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_delete_organization__check_successful_deletion(
    mocked_helpers: mock.MagicMock,
    mocked_rabbitmq_manager: mock.MagicMock,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    organization_owner_id: str,
    organization_id: str,
):
    """Test if the endpoint returns 204 when the organization is successfully deleted."""
    respx_mock.delete(f"/admin/realms/vantage/organizations/{organization_id}").mock(return_value=Response(204))

    mocked_rabbitmq_manager.call = mock.AsyncMock(return_value="dummy")
    mocked_helpers.notify_users_about_org_deletion = mock.AsyncMock(return_value=None)
    mocked_helpers.is_cloud_accounts_available_for_deletion = mock.AsyncMock(return_value=True)

    inject_security_header(organization_owner_id)  # sub will match the organization owner in token
    response = await test_client.delete("/admin/management/organizations")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mocked_rabbitmq_manager.call.assert_awaited_once_with(
        json.dumps({"tenant": organization_id, "action": "delete_organization"}).encode("utf-8")
    )
    mocked_helpers.notify_users_about_org_deletion.assert_awaited_once_with(organization_id=organization_id)
    mocked_helpers.is_cloud_accounts_available_for_deletion.assert_awaited_once_with(
        organization_id=organization_id
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_delete_organization__check_cloud_accounts_in_use(
    mocked_helpers: mock.MagicMock,
    mocked_rabbitmq_manager: mock.MagicMock,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    organization_owner_id: str,
    organization_id: str,
):
    """Test if the endpoint returns 400 when there are cloud accounts in use."""
    mocked_rabbitmq_manager.call = mock.AsyncMock(return_value="dummy")
    mocked_helpers.is_cloud_accounts_available_for_deletion = mock.AsyncMock(return_value=False)

    inject_security_header(organization_owner_id)
    response = await test_client.delete("/admin/management/organizations")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == "Not possible to delete organization due to cloud accounts in use."
    assert respx_mock.calls.call_count == 0
    mocked_helpers.is_cloud_accounts_available_for_deletion.assert_awaited_once_with(
        organization_id=organization_id
    )
    mocked_rabbitmq_manager.call.assert_not_awaited()


@pytest.mark.asyncio
@mock.patch("api.routers.organizations.rabbitmq_manager")
@mock.patch("api.routers.organizations.helpers")
async def test_delete_organization__check_failure__caller_is_not_owner(
    mocked_helpers: mock.MagicMock,
    mocked_rabbitmq_manager: mock.MagicMock,
    test_client: AsyncClient,
    inject_security_header: Callable,
    organization_owner_id: str,
):
    """Test if the endpoint returns 400 when the caller isn't the owner of the organization."""
    mocked_rabbitmq_manager.call = mock.AsyncMock(return_value="dummy")
    mocked_helpers.notify_users_about_org_deletion = mock.AsyncMock(return_value=None)

    assert organization_owner_id != "dummy-sub"  # make sure the caller is not the organization owner

    inject_security_header("dummy-sub")  # sub will match the organization owner in token
    response = await test_client.delete("/admin/management/organizations")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == "Caller is not the organization owner"
    mocked_rabbitmq_manager.call.assert_not_awaited()
    mocked_helpers.notify_users_about_org_deletion.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize("sub", ["grumpy-goose", "silly-squirel", "wacky-wombat"])
async def test_update_user_profile__user_not_found(
    sub: str,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test if the endpoint returns 404 when the user is not found."""
    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(404))

    inject_security_header(sub)
    response = await test_client.put("/admin/management/organizations/members/me", json={"first_name": "bar"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "User doesn't exist"


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_update_user_profile__invalid_input_body(
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
):
    """Test if the endpoint returns 422 when no input is passed in the body.

    This test is useful because all fields are optional, so we need to make
    sure that at least one field is provided.
    """
    sub = "John Doe"

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(return_value=Response(404))

    inject_security_header(sub)
    response = await test_client.put("/admin/management/organizations/members/me", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "At least one field must be provided."


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub, first_name",
    [
        ("grumpy-goose", "Grumpy"),
        ("silly-squirel", "Silly"),
        ("wacky-wombat", "Wacky"),
    ],
)
async def test_update_user_profile__update_first_name(
    sub: str,
    first_name: str,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_user_by_id_response_data: dict[
        str, str | bool | list[str | dict[str, str]] | int | dict[str, bool | list[str]]
    ],
):
    """Test if the endpoint correctly updates the user's first name."""
    get_user_by_id_response_data["id"] = sub

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json=get_user_by_id_response_data)
    )

    modified_user = get_user_by_id_response_data.copy()
    modified_user["firstName"] = first_name
    respx_mock.put(f"/admin/realms/vantage/users/{sub}", json=modified_user).mock(return_value=Response(204))

    inject_security_header(sub)
    response = await test_client.put(
        "/admin/management/organizations/members/me", json={"first_name": first_name}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "user_id": sub,
        "email": get_user_by_id_response_data["email"],
        "name": first_name + " " + get_user_by_id_response_data["lastName"],
        "avatar_url": None,
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub, last_name",
    [
        ("grumpy-goose", "Goose"),
        ("silly-squirel", "Squirel"),
        ("wacky-wombat", "Wombat"),
    ],
)
async def test_update_user_profile__update_last_name(
    sub: str,
    last_name: str,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_user_by_id_response_data: dict[
        str, str | bool | list[str | dict[str, str]] | int | dict[str, bool | list[str]]
    ],
):
    """Test if the endpoint correctly updates the user's last name."""
    get_user_by_id_response_data["id"] = sub

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json=get_user_by_id_response_data)
    )

    modified_user = get_user_by_id_response_data.copy()
    modified_user["lastName"] = last_name
    respx_mock.put(f"/admin/realms/vantage/users/{sub}", json=modified_user).mock(return_value=Response(204))

    inject_security_header(sub)
    response = await test_client.put(
        "/admin/management/organizations/members/me", json={"last_name": last_name}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "user_id": sub,
        "email": get_user_by_id_response_data["email"],
        "name": get_user_by_id_response_data["firstName"] + " " + last_name,
        "avatar_url": None,
    }


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub, avatar_url",
    [
        ("grumpy-goose", "https://avatar.com/grumpy-goose"),
        ("silly-squirel", "https://avatar.com/silly-squirel"),
        ("wacky-wombat", "https://avatar.com/wacky-wombat"),
    ],
)
async def test_update_user_profile__update_avatar_url(
    sub: str,
    avatar_url: str,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    get_user_by_id_response_data: dict[
        str, str | bool | list[str | dict[str, str]] | int | dict[str, bool | list[str]]
    ],
):
    """Test if the endpoint correctly updates the user's last name."""
    get_user_by_id_response_data["id"] = sub

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json=get_user_by_id_response_data)
    )

    modified_user = get_user_by_id_response_data.copy()
    modified_user["attributes"]["picture"] = [avatar_url]
    respx_mock.put(
        f"/admin/realms/vantage/users/{sub}",
        json=modified_user,
    ).mock(return_value=Response(204))

    inject_security_header(sub)
    response = await test_client.put(
        "/admin/management/organizations/members/me", json={"avatar_url": avatar_url}
    )
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data == {
        "user_id": sub,
        "email": get_user_by_id_response_data["email"],
        "name": get_user_by_id_response_data["firstName"] + " " + get_user_by_id_response_data["lastName"],
        "avatar_url": avatar_url,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("is_user_invited", [True, False])
async def test_user_has_pending_invites__check_when_returns_with_success(
    is_user_invited: bool,
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: Generator[str, None, None],
):
    """Test if the check_user_has_pending_invites endpoint returns the expected response."""
    sub = str(uuid.uuid4())

    user_attributes = {
        "inviter": [requester_email],
    } if is_user_invited else {}

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json={"id": sub, "attributes": user_attributes})
    )

    inject_security_header(sub)
    response = await test_client.get("/admin/management/organizations/invites/self-check")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"invited": is_user_invited}



@pytest.mark.asyncio
async def test_user_has_pending_invites__check_when_it_get_an_error(
    respx_mock: MockRouter,
    test_client: AsyncClient,
    inject_security_header: Callable,
    requester_email: Generator[str, None, None],
):
    """Test when the check_user_has_pending_invites endpoint returns with error."""
    sub = str(uuid.uuid4())

    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(400)
    )

    inject_security_header(sub)
    response = await test_client.get("/admin/management/organizations/invites/self-check")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
