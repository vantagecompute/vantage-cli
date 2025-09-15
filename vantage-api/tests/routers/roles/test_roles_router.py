"""Core module for testing the roles router."""
from collections.abc import Callable
from typing import Any, Dict, List, Union

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from respx.router import MockRouter

from api.body.output import RoleListModel, RoleModel, UserListModel
from api.identity.management_api import backend_client
from api.routers.roles.helpers import ListRolesSortFieldChecker, ListUsersByRoleSortFieldChecker
from api.utils.helpers import mount_users_list


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles__check_if_mocked_roles_are_returned(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the mocked roles."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles",
    ).mock(return_value=Response(200, json=role_list_example))

    inject_security_header("me", "admin:roles:read")
    response = await test_client.get("/admin/management/roles", params={"after": page, "per_page": per_page})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(roles=role_list_example, total=len(role_list_example)).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles__check_internal_error_behaviour(
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 500 when an internal error happens."""
    page = 0
    per_page = 100
    search = "whatever"
    error_message = "Something happened"

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles",
        params={"search": search},
    ).mock(return_value=Response(500, json={"error": error_message}))

    inject_security_header("me", "admin:roles:read")
    response = await test_client.get(
        "/admin/management/roles", params={"search": search, "after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles__check_if_empty_roles_response_returns_200_from_api(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 200 when the API returns an empty list of roles."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles",
    ).mock(return_value=Response(200, json=[]))

    inject_security_header("me", "admin:roles:read")
    response = await test_client.get("/admin/management/roles", params={"after": page, "per_page": per_page})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(roles=[], total=0).dict()


@pytest.mark.parametrize("sort_field", ListRolesSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles__test_sorting_over_fields(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
    sort_field: str,
):
    """Test if the endpoint returns the roles sorted by the given field."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles",
    ).mock(return_value=Response(200, json=role_list_example))

    inject_security_header("me", "admin:roles:read")

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/roles",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == RoleListModel(
            roles=sorted(role_list_example, key=lambda role: role[sort_field], reverse=not sort_ascending),
            total=len(role_list_example),
        ).dict()
    )

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/roles",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == RoleListModel(
            roles=sorted(role_list_example, key=lambda role: role[sort_field], reverse=not sort_ascending),
            total=len(role_list_example),
        ).dict()
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_role_by_name__check_if_returns_200_when_role_exists(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 200 when the role exists."""
    role = role_list_example[0]

    respx_mock.get(f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role.get('name')}").mock(
        return_value=Response(200, json=role)
    )

    inject_security_header("me", "admin:roles:read")

    response = await test_client.get(f"/admin/management/roles/{role.get('name')}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleModel(**role).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_role_by_name__check_if_returns_404_when_role_doesnt_exist(
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when the role doesn't exist."""
    role_name = "dummy-role-name"

    respx_mock.get(f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role_name}").mock(
        return_value=Response(404)
    )

    inject_security_header("me", "admin:roles:read")

    response = await test_client.get(f"/admin/management/roles/{role_name}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_role_users__check_if_returns_200_when_role_exists(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 200 when the role exists."""
    page = 0
    per_page = 100

    role = role_list_example[0]

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role.get('name')}/users",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:roles:read")
    response = await test_client.get(
        f"/admin/management/roles/{role.get('name')}/users", params={"after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mount_users_list(dummy_user_list).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_role_users__check_if_returns_404_when_role_doesnt_exist(
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when the role doesn't exist."""
    page = 0
    per_page = 100

    role_name = "dummy-role-name"

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role_name}/users",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(404))

    inject_security_header("me", "admin:roles:read")
    response = await test_client.get(
        f"/admin/management/roles/{role_name}/users", params={"after": page, "per_page": per_page}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.parametrize("sort_field", ListUsersByRoleSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_role_users__check_sorting_over_user_fields(
    mock_fetch_default_client: None,
    role_list_example: List[Dict[str, Union[str, bool]]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    respx_mock: MockRouter,
    default_client: Dict[str, Any],
    inject_security_header: Callable,
    test_client: AsyncClient,
    sort_field: str,
):
    """Test if the endpoint returns the users sorted by the given field."""
    page = 0
    per_page = 100

    role = role_list_example[0]

    respx_mock.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role.get('name')}/users",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))

    inject_security_header("me", "admin:roles:read")

    sort_ascending = True
    response = await test_client.get(
        f"/admin/management/roles/{role.get('name')}/users",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    user_list_model = mount_users_list(dummy_user_list)

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
    )
    assert response.json() == UserListModel(users=sorted_users).dict()

    sort_ascending = False
    response = await test_client.get(
        f"/admin/management/roles/{role.get('name')}/users",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    sorted_users = sorted(
        user_list_model.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
    )
    assert response.json() == UserListModel(users=sorted_users).dict()
