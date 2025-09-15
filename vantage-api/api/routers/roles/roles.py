"""Routes for roles endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status

from api.body.output import MessageModel, RoleListModel, RoleModel, UserListModel
from api.identity.management_api import backend_client
from api.routers.roles.helpers import ListRolesSortFieldChecker, ListUsersByRoleSortFieldChecker
from api.settings import SETTINGS
from api.utils import response
from api.utils.helpers import fetch_default_client, mount_users_list

router = APIRouter()


@router.get(
    "/roles",
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:roles:read"))],
    responses={
        200: {"model": RoleModel, "description": "Users retrieved successfully"},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
    },
)
async def list_roles(
    search: Optional[str] = Query(None, description="Search groups by keyword. It's case-sensitive."),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, le=100, description="Number of results per page."),
    sort_field: Optional[str] = Depends(ListRolesSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
):
    """List all available roles."""
    default_client = await fetch_default_client()

    roles_response = await backend_client.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles",
        params={"search": search},
    )
    if roles_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **roles_response.json()))

    roles = roles_response.json()

    if sort_field is not None:
        roles = sorted(roles, key=lambda role: role[sort_field], reverse=not sort_ascending)

    roles_page = roles[after : after + per_page]
    return response.success(RoleListModel(roles=roles_page, total=len(roles)))


@router.get(
    "/roles/{role_name}",
    responses={
        200: {"model": RoleModel, "description": "Users retrieved successfully"},
        404: {"model": MessageModel, "description": "Couldn't find input role"},
    },
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:roles:read"))],
)
async def get_role_by_name(role_name: str = Path(..., description="Name of the role.")):
    """Fetch properties from role by name."""
    default_client = await fetch_default_client()

    role_response = await backend_client.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role_name}"
    )
    if role_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Role not found by name"))

    return response.success(RoleModel(**role_response.json()))


@router.get(
    "/roles/{role_name}/users",
    responses={
        200: {"model": UserListModel, "description": "Users retrieved successfully"},
        404: {"model": MessageModel, "description": "Couldn't find input role"},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
    },
    dependencies=[Depends(SETTINGS.GUARD.lockdown("admin:roles:read"))],
)
async def get_users_attached_to_role(
    role_name: str = Path(..., description="Name of the role."),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, le=100, description="Number of results per page."),
    sort_field: Optional[str] = Depends(ListUsersByRoleSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
):
    """Get the users from a role."""
    default_client = await fetch_default_client()

    users_response = await backend_client.get(
        f"/admin/realms/vantage/clients/{default_client.get('id')}/roles/{role_name}/users",
        params={"first": after, "max": per_page},
    )
    if users_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Role not found by name"))
    users = users_response.json()

    users_list = mount_users_list(users)

    if sort_field is not None:
        users_list.users = sorted(
            users_list.users, key=lambda user: getattr(user, sort_field) or "", reverse=not sort_ascending
        )
    return response.success(users_list)
