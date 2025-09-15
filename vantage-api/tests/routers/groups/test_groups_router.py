"""Core module for testing the groups endpoints."""
from collections.abc import Callable
from typing import Any, Dict, List, Union

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from respx.router import MockRouter

from api.body.output import GroupListModel, GroupModel, RoleListModel
from api.identity.management_api import backend_client
from api.routers.groups.helpers import (
    ListGroupsSortFieldChecker,
    ListRolesByGroupsSortFieldChecker,
    ListUsersByGroupSortFieldChecker,
)
from api.utils.helpers import mount_users_list


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups__check_request_response_when_theres_groups(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint returns the groups when there's groups."""
    page = 0
    per_page = 100

    respx_mock.get(
        "/admin/realms/vantage/groups", params={"first": page, "max": per_page, "briefRepresentation": False}
    ).mock(return_value=Response(200, json=[group_example]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get("/admin/management/groups", params={"after": page, "per_page": per_page})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupListModel(
        groups=[GroupModel(**group_example, roles=group_example.get("clientRoles").get("default"))]
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups__check_request_response_when_theres_no_groups(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint returns an empty list when there's no groups."""
    page = 0
    per_page = 100

    respx_mock.get(
        "/admin/realms/vantage/groups", params={"first": page, "max": per_page, "briefRepresentation": False}
    ).mock(return_value=Response(200, json=[]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get("/admin/management/groups", params={"after": page, "per_page": per_page})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupListModel(groups=[])


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups__check_request_response_when_the_group_has_no_roles(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint returns the group when it has no roles."""
    page = 0
    per_page = 100

    group_example.update(clientRoles={})

    respx_mock.get(
        "/admin/realms/vantage/groups", params={"first": page, "max": per_page, "briefRepresentation": False}
    ).mock(return_value=Response(200, json=[group_example]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get("/admin/management/groups", params={"after": page, "per_page": per_page})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupListModel(groups=[GroupModel(**group_example, roles=[])])


@pytest.mark.parametrize("sort_field", ListGroupsSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups__check_if_its_possible_to_sort(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    sort_field: str,
):
    """Test if the endpoint can sort over correct fields."""
    page = 0
    per_page = 100
    search = "whatever"

    respx_mock.get(
        "/admin/realms/vantage/groups",
        params={"first": page, "max": per_page, "briefRepresentation": False, "search": search},
    ).mock(return_value=Response(200, json=[group_example]))

    expected_payload = GroupListModel(
        groups=[
            GroupModel(
                **group_example,
                roles=group_example.get("clientRoles").get("default"),
            )
        ]
    )

    inject_security_header("me", "admin:groups:read")

    sort_ascending = True
    response = await test_client.get(
        "/admin/management/groups",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    expected_payload.groups = sorted(
        expected_payload.groups, key=lambda group: getattr(group, sort_field), reverse=not sort_ascending
    )
    assert response.json() == expected_payload

    sort_ascending = False
    response = await test_client.get(
        "/admin/management/groups",
        params={
            "search": search,
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    expected_payload.groups = sorted(
        expected_payload.groups, key=lambda group: getattr(group, sort_field), reverse=not sort_ascending
    )
    assert response.json() == expected_payload


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_groups__assert_if_search_parameter_is_passed(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint can search for groups."""
    page = 0
    per_page = 100
    search = "omnivector"

    respx_mock.get(
        "/admin/realms/vantage/groups",
        params={"first": page, "max": per_page, "briefRepresentation": False, "search": search},
    ).mock(return_value=Response(200, json=[group_example]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        "/admin/management/groups", params={"after": page, "per_page": per_page, "search": search}
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles_from_a_group__check_request_response_when_the_group_exists__check_when_the_group_has_no_roles(  # noqa: E501
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    default_client: Dict[str, Any],
):
    """Test if the endpoint returns an empty list when the group has no roles."""
    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/role-mappings/clients/{default_client.get('id')}"
    ).mock(return_value=Response(200, json=[]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_example.get('id')}/roles")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(roles=[], total=0)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles_from_a_group__check_request_response_when_the_group_exists__check_when_the_group_has_roles(  # noqa: E501
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    default_client: Dict[str, Any],
    role_list_example: List[Dict[str, Union[str, bool]]],
):
    """Test if the endpoint returns the roles when the group has roles."""
    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/role-mappings/clients/{default_client.get('id')}"
    ).mock(return_value=Response(200, json=role_list_example))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_example.get('id')}/roles")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(roles=role_list_example, total=len(role_list_example))


@pytest.mark.parametrize("sort_field", ListRolesByGroupsSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles_from_a_group__check_sorting__check_request_response_when_the_group_exists__check_when_the_group_has_roles(  # noqa: E501
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    default_client: Dict[str, Any],
    role_list_example: List[Dict[str, Union[str, bool]]],
    sort_field: str,
):
    """Test if the endpoint can sort over correct fields."""
    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/role-mappings/clients/{default_client.get('id')}"
    ).mock(return_value=Response(200, json=role_list_example))

    inject_security_header("me", "admin:groups:read")

    sort_ascending = True
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/roles",
        params={"sort_field": sort_field, "sort_ascending": sort_ascending},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(
        roles=sorted(role_list_example, key=lambda role: role[sort_field], reverse=not sort_ascending),
        total=len(role_list_example),
    )

    sort_ascending = False
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/roles",
        params={"sort_field": sort_field, "sort_ascending": sort_ascending},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == RoleListModel(
        roles=sorted(role_list_example, key=lambda role: role[sort_field], reverse=not sort_ascending),
        total=len(role_list_example),
    )


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_roles_from_a_group__check_request_response_when_the_group_doesnt_exist(
    mock_fetch_default_client: None,
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    default_client: Dict[str, Any],
    role_list_example: List[Dict[str, Union[str, bool]]],
):
    """Test if the endpoint returns 404 when the group doesn't exist."""
    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/role-mappings/clients/{default_client.get('id')}"
    ).mock(return_value=Response(404))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_example.get('id')}/roles")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_exists__check_when_theres_no_users(  # noqa: E501
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint returns 500 when an unexpected error happens."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=[]))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mount_users_list([])


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_exists__check_when_theres_users__all_members_of_organization(  # noqa: E501
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    sample_uuid: str,
):
    """Test if the endpoint returns 500 when an unexpected error happens."""
    page = 0
    per_page = 100
    max_user_query = 2147483647

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))

    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"max": max_user_query}
    ).mock(
        return_value=Response(200, json=dummy_user_list)
    )

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mount_users_list(dummy_user_list)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_exists__check_when_theres_users__not_all_members_of_organization(  # noqa: E501
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    sample_uuid: str,
):
    """Test if the endpoint returns 500 when an unexpected error happens."""
    page = 0
    per_page = 100
    max_user_query = 2147483647

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"max": max_user_query}
    ).mock(
        return_value=Response(200, json=dummy_user_list[:-1])
    )

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mount_users_list(dummy_user_list[:-1])


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_exists__check_when_theres_users__not_all_members_of_organization__internal_error_fetching_members(  # noqa: E501
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    sample_uuid: str,
):
    """Test if the endpoint returns 500 when an unexpected error happens."""
    page = 0
    per_page = 100
    error_message = "Something happened"
    max_user_query = 2147483647

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"max": max_user_query}
    ).mock(
        return_value=Response(500, json={"error": error_message})
    )

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"] == error_message


@pytest.mark.parametrize("sort_field", ListUsersByGroupSortFieldChecker.available_fields())
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_exists__check_sorting_over_user_fields(  # noqa: E501
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
    dummy_user_list: List[Dict[str, Union[str, bool, int]]],
    sort_field: str,
    sample_uuid: str,
):
    """Test if the endpoint can sort over user fields."""
    page = 0
    per_page = 100
    max_user_query = 2147483647

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(200, json=dummy_user_list))
    respx_mock.get(
        f"/admin/realms/vantage/organizations/{sample_uuid}/members",
        params={"max": max_user_query}
    ).mock(
        return_value=Response(200, json=dummy_user_list)
    )

    inject_security_header("me", "admin:groups:read")

    expected_payload = mount_users_list(dummy_user_list)

    sort_ascending = True
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    expected_payload.users = sorted(
        expected_payload.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
    )
    assert response.json() == expected_payload

    sort_ascending = False
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={
            "after": page,
            "per_page": per_page,
            "sort_field": sort_field,
            "sort_ascending": sort_ascending,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    expected_payload.users = sorted(
        expected_payload.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
    )
    assert response.json() == expected_payload


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_users_who_belong_to_a_group__check_request_response_when_the_group_doesn_exist(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    group_example: Dict[str, Union[str, Dict, List]],
):
    """Test if the endpoint returns 404 when the group doesn't exist."""
    page = 0
    per_page = 100

    respx_mock.get(
        f"/admin/realms/vantage/groups/{group_example.get('id')}/members",
        params={"first": page, "max": per_page},
    ).mock(return_value=Response(404))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(
        f"/admin/management/groups/{group_example.get('id')}/users",
        params={"after": page, "per_page": per_page},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_group__check_request_response_when_the_group_doesn_exist(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns 404 when the group doesn't exist."""
    group_id = "123456789"

    respx_mock.get(f"/admin/realms/vantage/groups/{group_id}").mock(return_value=Response(404))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "message" in response.json()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_group__check_request_response_when_the_group_has_no_description(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the group when it has no description."""
    group_id = "123456789"

    group = {"id": group_id, "name": "dummy name", "clientRoles": {"default": ["dummy role"]}}

    respx_mock.get(f"/admin/realms/vantage/groups/{group_id}").mock(return_value=Response(200, json=group))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == GroupModel(**group, roles=group.get("clientRoles").get("default")).dict()


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_fetch_group__check_request_response_when_the_group_has_no_roles(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test if the endpoint returns the group when it has no roles."""
    group_id = "123456789"

    group = {"id": group_id, "name": "dummy name", "attributes": {"description": ["dummy description"]}}

    respx_mock.get(f"/admin/realms/vantage/groups/{group_id}").mock(return_value=Response(200, json=group))

    inject_security_header("me", "admin:groups:read")
    response = await test_client.get(f"/admin/management/groups/{group_id}")

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == GroupModel(**group, description=group.get("attributes").get("description")[0]).dict()
    )
