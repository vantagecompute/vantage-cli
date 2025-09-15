"""Groups router."""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, Path, Query, status

from api.body.output import (
    GroupListModel,
    GroupModel,
    MessageModel,
    RoleListModel,
    UserListModel,
)
from api.identity.management_api import backend_client
from api.routers.groups.helpers import (
    ListGroupsSortFieldChecker,
    ListRolesByGroupsSortFieldChecker,
    ListUsersByGroupSortFieldChecker,
)
from api.settings import SETTINGS
from api.utils import response
from api.utils.helpers import (
    fetch_default_client,
    mount_users_list,
    unpack_organization_id_from_token,
)
from api.utils.logging import logger

router = APIRouter()


@router.get(
    "/groups",
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:groups:read"))],
    responses={200: {"model": GroupListModel, "description": "Groups retrieved successfully"}},
)
async def list_groups(
    search: Optional[str] = Query(None, description="Search groups by keyword. It's case-sensitive."),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, description="Number of results per page."),
    sort_field: Optional[str] = Depends(ListGroupsSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
):
    """List groups based on search parameter. If none is passed, then list by order."""
    groups_response = await backend_client.get(
        "/admin/realms/vantage/groups",
        params={"first": after, "max": per_page, "briefRepresentation": False, "search": search},
    )
    groups = groups_response.json()
    for i, group in enumerate(groups):
        try:
            logger.debug(group)
            groups[i] = {
                "id": group.get("id"),
                "name": group.get("name"),
                "roles": list(group.get("clientRoles").get("default")),
            }
        except TypeError:
            logger.debug(f"Tried to get roles from the group {group.get('name')} but no role was found.")
            groups[i] = {"id": group.get("id"), "name": group.get("name"), "roles": []}
        finally:
            groups[i] = GroupModel(**groups[i])
    if sort_field is not None:
        groups = sorted(groups, key=lambda group: getattr(group, sort_field), reverse=not sort_ascending)
    return response.success(GroupListModel(groups=groups))


@router.get(
    "/groups/{group_id}",
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:groups:read"))],
    responses={200: {"model": GroupModel, "description": "Group fetched successfully"}},
)
async def fetch_group(
    group_id: str = Path(..., description="ID of the group to fetch"),
):
    """Fetch a group by its ID."""
    group_response = await backend_client.get(f"/admin/realms/vantage/groups/{group_id}")

    if group_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Input group doesn't exist."))

    group = group_response.json()

    try:
        group.update(description=group["attributes"]["description"][0])
    except KeyError:
        pass

    try:
        group.update(roles=group["clientRoles"]["default"])
    except KeyError:
        pass
    return response.success(GroupModel(**group))


@router.get(
    "/groups/{group_id}/roles",
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:groups:read"))],
    responses={200: {"model": RoleListModel, "description": "Roles retrieved successfully"}},
)
async def list_permissions_by_group(
    group_id: str = Path(..., description="Role ID to which retrieve the attached permissions"),
    sort_field: Optional[str] = Depends(ListRolesByGroupsSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
):
    """List all roles from a group."""
    default_client = await fetch_default_client()

    # fetch role-mapping
    role_mapping_response = await backend_client.get(
        f"/admin/realms/vantage/groups/{group_id}/role-mappings/clients/{default_client.get('id')}"
    )
    if role_mapping_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Group not found by id"))

    roles = {"roles": role_mapping_response.json()}

    if sort_field is not None:
        roles.update(
            roles=sorted(
                roles.get("roles"),
                key=lambda role: role[sort_field],
                reverse=not sort_ascending,
            )
        )

    return response.success(RoleListModel(**roles, total=len(roles.get("roles"))))


@router.get(
    "/groups/{group_id}/users",
    responses={
        200: {"model": UserListModel, "description": "Users retrieved successfully"},
        404: {"model": MessageModel, "description": "Group not found"},
        500: {"model": MessageModel, "description": "Internal error"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
    },
)
async def list_users_from_a_group(
    group_id: str = Path(..., description="Group ID for which to retrieve the attached users"),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, le=100, description="Number of results per page."),
    sort_field: Optional[str] = Depends(ListUsersByGroupSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:groups:read")),
):
    """Retrieve users associated with a group."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    group_response = await backend_client.get(
        f"/admin/realms/vantage/groups/{group_id}/members",
        params={
            "first": after,
            "max": per_page,
        },
    )

    if group_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Group not found by id"))

    users = group_response.json()
    max_user_query = 2147483647

    if len(users) > 0:
        # fetch all users in the organization
        all_members_response = await backend_client.get(
            f"/admin/realms/vantage/organizations/{organization_id}/members", params={"max": max_user_query}
        )
        if all_members_response.status_code != status.HTTP_200_OK:
            return response.internal_error(
                MessageModel(message="Internal error", **all_members_response.json())
            )

        # filter users who belong to the caller's organization
        members_ids = [member["id"] for member in all_members_response.json()]
        members_belonging_to_group = filter(lambda member: member["id"] in members_ids, users)

        users_list = mount_users_list(list(members_belonging_to_group))
    else:
        users_list = mount_users_list([])

    if sort_field is not None:
        users_list.users = sorted(
            users_list.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
        )

    return response.success(users_list)
