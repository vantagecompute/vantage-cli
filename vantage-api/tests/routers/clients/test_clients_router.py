"""Tests for the clients router."""
from collections.abc import Callable
from typing import Any, Dict

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from respx.router import MockRouter

from api.body.output import ClientListModel, ClientModel
from api.identity.management_api import backend_client
from api.routers.clients.helpers import ListClientsSortFieldChecker


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_client_by_id_when_client_doesnt_belong_to_organization(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test fetching a client by id when the client doesn't belong to the organization."""
    assert sample_uuid != "545d2a23-bf91-41e1-a748-32a6f40dbf33"

    foo_client = {
        "id": "545d2a23-bf91-41e1-a748-32a6f40dbf33",
        "clientId": "foo-545d2a23-bf91-41e1-a748-32a6f40dbf33",
        "name": "545d2a23-bf91-41e1-a748-32a6f40dbf33",
        "description": "",
        "rootUrl": "",
        "adminUrl": "",
        "baseUrl": "",
        "surrogateAuthRequired": False,
        "enabled": True,
        "alwaysDisplayInConsole": False,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["/*"],
        "webOrigins": ["/*"],
        "notBefore": 0,
        "bearerOnly": False,
        "consentRequired": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "publicClient": True,
        "frontchannelLogout": True,
        "protocol": "openid-connect",
        "attributes": {
            "oidc.ciba.grant.enabled": "false",
            "oauth2.device.authorization.grant.enabled": "false",
            "display.on.consent.screen": "false",
            "backchannel.logout.session.required": "true",
            "backchannel.logout.revoke.offline.tokens": "false",
        },
        "authenticationFlowBindingOverrides": {},
        "fullScopeAllowed": True,
        "nodeReRegistrationTimeout": -1,
        "defaultClientScopes": ["web-origins", "acr", "profile", "roles", "email", "roles-in-token"],
        "optionalClientScopes": ["address", "phone", "org-in-token", "offline_access", "microprofile-jwt"],
        "access": {"view": True, "configure": True, "manage": True},
    }

    respx_mock.get(f"/admin/realms/vantage/clients/{foo_client.get('id')}").mock(
        return_value=Response(200, json=foo_client)
    )

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(f"/admin/management/clients/{foo_client.get('id')}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_client_by_id_when_client_exists(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test fetching a client by id when the client exists."""
    client_secret = "dummy-secret"
    foo_client = {
        "id": "545d2a23-bf91-41e1-a748-32a6f40dbf33",
        "clientId": f"foo-{sample_uuid}",
        "name": f"{sample_uuid}",
        "description": "",
        "rootUrl": "",
        "adminUrl": "",
        "baseUrl": "",
        "surrogateAuthRequired": False,
        "enabled": True,
        "alwaysDisplayInConsole": False,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["/*"],
        "webOrigins": ["/*"],
        "notBefore": 0,
        "bearerOnly": False,
        "consentRequired": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "publicClient": True,
        "frontchannelLogout": True,
        "protocol": "openid-connect",
        "attributes": {
            "oidc.ciba.grant.enabled": "false",
            "oauth2.device.authorization.grant.enabled": "false",
            "display.on.consent.screen": "false",
            "backchannel.logout.session.required": "true",
            "backchannel.logout.revoke.offline.tokens": "false",
        },
        "authenticationFlowBindingOverrides": {},
        "fullScopeAllowed": True,
        "nodeReRegistrationTimeout": -1,
        "defaultClientScopes": ["web-origins", "acr", "profile", "roles", "email", "roles-in-token"],
        "optionalClientScopes": ["address", "phone", "org-in-token", "offline_access", "microprofile-jwt"],
        "access": {"view": True, "configure": True, "manage": True},
    }

    respx_mock.get(f"/admin/realms/vantage/clients/{foo_client.get('id')}").mock(
        return_value=Response(200, json=foo_client)
    )
    respx_mock.get(f"/admin/realms/vantage/clients/{foo_client.get('id')}/client-secret").mock(
        return_value=Response(200, json={"type": "secret", "value": client_secret})
    )

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(f"/admin/management/clients/{foo_client.get('id')}")

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == ClientModel(
            **foo_client,
            clientSecret=client_secret,
        ).dict()
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url), assert_all_called=False)
async def test_fetch_client_by_id__test_404_when_client_doesnt_exist(
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test fetching a client by id when the client doesn't exist."""
    respx_mock.get(f"/admin/realms/vantage/clients/{default_client.get('id')}").mock(
        return_value=Response(404)
    )
    client_secret_request = respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/client-secret"
    )

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(f"/admin/management/clients/{default_client.get('id')}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()
    assert not client_secret_request.called


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__check_if_mocked_clients_are_returned(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
):
    """Test fetching clients when the response is not empty."""
    page = 0
    per_page = 100

    clients = [
        {
            "name": "blablabla",
            "description": "dummy description",
            "id": "abcdefghijklmn",
            "clientId": f"dummy-{sample_uuid}",
        }
    ]

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=clients))

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(
        "/admin/management/clients", params={"after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ClientListModel(clients=clients).dict()


@pytest.mark.parametrize("sort_field", ListClientsSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__sorting_over_fields(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    sort_field: str,
):
    """Test fetching clients and sorting by available fields."""
    page = 0
    per_page = 100

    clients = [
        {
            "name": "dummy1",
            "description": "dummy description 1",
            "id": "abcdefghijklmn",
            "clientId": f"dummy1-{sample_uuid}",
        },
        {
            "name": "dummy2",
            "description": "dummy description 2",
            "id": "nmlkjihgfedcba",
            "clientId": f"dummy2-{sample_uuid}",
        },
    ]

    expected_payload = ClientListModel(clients=clients)

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=clients))

    inject_security_header("me", "admin:clients:read")

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/clients",
        params={
            "page": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ClientListModel(
        clients=sorted(
            expected_payload.clients,
            key=lambda client: getattr(client, sort_field),
            reverse=not sort_ascending,
        )
    )

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/clients",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ClientListModel(
        clients=sorted(
            expected_payload.clients,
            key=lambda client: getattr(client, sort_field),
            reverse=not sort_ascending,
        )
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__check_internal_error_fetching_clients(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test fetching clients when there's an internal error."""
    page = 0
    per_page = 100

    error_message = "Something happened"

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(500, json={"error": error_message}))

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(
        "/admin/management/clients", params={"after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__check_if_empty_clients_response_returns_200_from_api(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test fetching clients when the response is empty."""
    page = 0
    per_page = 100

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=[]))

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(
        "/admin/management/clients", params={"after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ClientListModel(clients=[]).dict()


@pytest.mark.parametrize("client_id", [("dummy-1"), ("dummy-2"), ("dummy-3")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__check_search_by_client_id__check_response_not_empty(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    client_id: str,
):
    """Test fetching clients by client_id when the response is not empty."""
    page = 0
    per_page = 100

    clients = [
        {
            "name": "blablabla",
            "description": "dummy description",
            "id": "abcdefghijklmn",
            "clientId": f"{client_id}-{sample_uuid}",
        }
    ]

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page, "search": True, "clientId": client_id},
    ).mock(return_value=Response(200, json=clients))

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(
        "/admin/management/clients", params={"after": page, "per_page": per_page, "client_id": client_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ClientListModel(clients=clients).dict()


@pytest.mark.parametrize("client_id", [("dummy-1"), ("dummy-2"), ("dummy-3")])
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_clients__check_search_by_client_id__check_response_empty(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sample_uuid: str,
    client_id: str,
):
    """Test fetching clients by client_id when the response is empty."""
    page = 0
    per_page = 100

    clients = [
        {
            "name": "blablabla",
            "description": "dummy description",
            "id": "abcdefghijklmn",
            "clientId": client_id,
        }
    ]

    respx_mock.get(
        "/admin/realms/vantage/clients",
        params={"first": page, "max": per_page, "search": True, "clientId": client_id},
    ).mock(return_value=Response(200, json=clients))

    inject_security_header("me", "admin:clients:read")
    response = await test_client.get(
        "/admin/management/clients", params={"after": page, "per_page": per_page, "client_id": client_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"clients": []}
