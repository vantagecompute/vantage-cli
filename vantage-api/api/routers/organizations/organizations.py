"""Organizations endpoints."""
import asyncio
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

import httpx
from armasec import TokenPayload
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response, status
from loguru import logger

from api.body.input import (
    AzureIdPModel,
    CreateOrganizationModel,
    GitHubIdPModel,
    GoogleIdPModel,
    InputGroupsModel,
    InviteModel,
    PatchAzureIdpModel,
    PatchGitHubIdpModel,
    PatchGoogleIdpModel,
    UpdateOrganizationModel,
    UpdateUserProfile,
)
from api.body.output import (
    CompleteUserModel,
    GroupAttachmentResults,
    GroupListModel,
    IdPModel,
    IdPsListModel,
    IsOrgNameAvailableModel,
    IsUserInvited,
    MessageModel,
    OrganizationAttributesModel,
    OrganizationModel,
    UserListModel,
    UserModel,
)
from api.broker_app.helpers import create_organization_action_payload, delete_organization_action_payload
from api.broker_app.rpc_client import rabbitmq_manager
from api.identity.management_api import backend_client
from api.routers.organizations import helpers
from api.schemas.keycloak import KeycloakOrganizationModel
from api.settings import SETTINGS
from api.utils import response
from api.utils.helpers import (
    fetch_users_count,
    mount_users_list,
    unpack_organization_id_from_token,
    unpack_owner_id_from_token,
)

router = APIRouter()


@router.get(
    "/organizations/check-existing/{name}",
    dependencies=[Depends(SETTINGS.GUARD.lockdown())],
    response_model=IsOrgNameAvailableModel,
    status_code=status.HTTP_200_OK,
)
async def check_existing_organization_by_name(name: str = Path(..., description="Name of the organization.")):
    """Check whether or not an organization exists given its name."""
    is_name_available = await helpers.is_organization_name_available(name)
    return response.success(IsOrgNameAvailableModel(available=is_name_available))


@router.post(
    "/organizations",
    responses={
        201: {"model": OrganizationModel, "description": "Organization created successfully"},
        500: {"model": MessageModel, "description": "Unknown error, contact support"},
        409: {"model": MessageModel, "description": "Organization name already in use"},
        400: {"model": MessageModel, "description": "User already belong to an organization"},
    },
)
async def create_organization(  # noqa: C901
    body: CreateOrganizationModel, decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown())
):
    """Create an organization."""
    # check if user already belongs to any organization
    user_orgs_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/members/{decoded_token.sub}/organizations"
    )
    if user_orgs_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **user_orgs_response.json()))

    # return 400 if user already belongs to an organization
    if len(user_orgs_response.json()) > 0:
        return response.bad_request(MessageModel(message="User already belongs to an organization"))

    creation_time = datetime.now().timestamp()
    org_name = helpers.parse_org_name(body.name)

    prefix = "app" if SETTINGS.STAGE == 'production' else f"app.{SETTINGS.STAGE}"

    org_creation_payload = {
        "name": org_name,
        "alias": org_name,
        "domains": [{
            "name": org_name,
        }],
        # necessary for Keycloak to work invitations
        "redirectUrl": f"https://{prefix}.{SETTINGS.APP_DOMAIN}/",
        "attributes": {
            "logo": [body.logo],
            "created_at": [creation_time],
            "owner": [decoded_token.sub],
            "display_name": [body.display_name],
        },
    }

    org_response = await backend_client.post("/admin/realms/vantage/organizations", json=org_creation_payload)
    logger.debug(f"Response from Keycloak: {org_response.status_code} - {org_response.content}")

    if org_response.status_code == status.HTTP_409_CONFLICT:
        return response.conflict(MessageModel(message="Organization name already in use."))

    if org_response.status_code != status.HTTP_201_CREATED:
        return response.internal_error(MessageModel(message="Unknown error", **org_response.json()))

    # fetch organization so we can have the ID
    fetch_org_response = await backend_client.get(
        "/admin/realms/vantage/organizations", params={"search": org_name, "max": 1, "first": 0}
    )
    fetched_org = fetch_org_response.json()[0]

    org_id = fetched_org.get("id")
    # remove default user and service-account-admin-ops from organization
    users_response = await backend_client.get(f"/admin/realms/vantage/organizations/{org_id}/members")
    for user in users_response.json():
       if user.get("username") == "service-account-admin-ops":
           await backend_client.delete(
               f"/admin/realms/vantage/organizations/{org_id}/members/{user.get('id')}"
            )
       elif user.get("username").startswith("org-admin"):
           await backend_client.delete(f"/admin/realms/vantage/users/{user.get('id')}")


    try:
        await helpers.add_admin_user_and_set_up_permissions(decoded_token.sub, org_id)
    except Exception:
        await backend_client.delete(f"/admin/realms/vantage/organizations/{org_id}")
        return response.internal_error(MessageModel(message="Internal error when setting up organization"))

    # publish message to RabbitMQ
    init = time.time()
    try:
        rpc_server_response = await rabbitmq_manager.call(create_organization_action_payload(org_id))
    except Exception as err:
        # rollback the whole transaction
        logger.exception(f"Failed to publish message to RabbitMQ: {err}")
        await backend_client.delete(f"/admin/realms/vantage/organizations/{org_id}")
        return response.internal_error(MessageModel(message="Error sending RabbitMQ message"))
    else:
        logger.success(f"Successfully received response from the RPC server: {rpc_server_response}")
    finally:
        logger.debug(
            f"Elapsed time to publish and receive response from the RPC server: {time.time() - init}"
        )

    return response.created(
        OrganizationModel(
            name=org_name,
            id=org_id,
            display_name=body.display_name,
            attributes=OrganizationAttributesModel(
                created_at=creation_time,
                logo=body.logo,
                owner=decoded_token.sub,
            ),
        ).dict()
    )


@router.patch(
    "/organizations",
    responses={
        200: {"model": MessageModel, "description": "Organization updated successfully"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
        500: {"model": MessageModel, "description": "Unknown error, contact support"},
    },
)
async def update_organization(
    body: UpdateOrganizationModel,
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:organizations:update")),
):
    """Update the organization settings.

    In case the *domain* field is not provided, the endpoint will remove the domain from the organization.
    """
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    org_response = await backend_client.get(f"/admin/realms/vantage/organizations/{organization_id}")
    org = org_response.json()
    organization = KeycloakOrganizationModel(
        id=org.get("id"),
        name=org.get("alias"),
        url=org.get("redirectUrl"),
        display_name=org.get("attributes", {}).get("display_name", [org.get("name")])[0],
        attributes=org.get("attributes", {}),
        domains=[domain["name"] for domain in org.get("domains", [])],
    )

    update_organization_payload = {
        "id": organization.id,
        "name": organization.name,
        "alias": organization.name,
        "redirectUrl": organization.url,
        "domains": [{"name": organization.domains[0]}] if body.domain is None and len(organization.domains) > 0 else [{"name": body.domain}], # noqa
        "attributes": organization.attributes,
    }

    update_organization_payload["attributes"]["display_name"] = [body.display_name or organization.display_name] # noqa
    update_organization_payload["attributes"]["logo"] = (
        [str(body.logo)] if body.logo else organization.attributes["logo"]
    )

    org_response = await backend_client.put(
        f"/admin/realms/vantage/organizations/{organization_id}", json=update_organization_payload
    )
    logger.debug(f"Request body to Keycloak: {update_organization_payload}")
    logger.debug(f"Response from Keycloak: {org_response.status_code} - {org_response.content}")
    if org_response.status_code != status.HTTP_204_NO_CONTENT:
        logger.error(f"Unknown error related to Keycloak: {org_response.json()}")
        return response.internal_error(MessageModel(message="Contact support", **org_response.json()).dict())

    # update the payload to match the response
    update_organization_payload["display_name"] = body.display_name or organization.display_name
    update_organization_payload["name"] = update_organization_payload["alias"]
    update_organization_payload["domains"] = [update_organization_payload["domains"][0].get("name", organization.name)] if body.domain is None else [body.domain] # noqa
    return response.success(OrganizationModel(**update_organization_payload).dict())


@router.delete(
    "/organizations",
    responses={
        204: {"description": "Organization deleted successfully."},
        400: {
            "model": MessageModel,
            "description": (
                "One of three possible errors: "
                "organization not found in token, "
                "organization owner not found in token, "
                "caller is not the organization owner, or"
                "there is at least one cloud account in use."
            ),
        },
        500: {"model": MessageModel, "description": "Unknown error, contact support."},
    },
)
async def delete_an_organization(decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown())):
    """Delete the organization which the caller belongs to."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization ID not found in token").dict())

    # check if caller is the organization owner
    try:
        owner_id = unpack_owner_id_from_token(decoded_token)
        logger.debug(f"Owner ID unpacked from token: {owner_id}")
    except KeyError as err:
        logger.debug(f"KeyError unpacking owner ID from token: {err}")
        return response.bad_request(MessageModel(message="Owner ID not found in token").dict())
    else:
        if owner_id != decoded_token.sub:
            return response.bad_request(MessageModel(message="Caller is not the organization owner").dict())

    can_delete_cloud_accounts = await helpers.is_cloud_accounts_available_for_deletion(
        organization_id=organization_id
    )
    if not can_delete_cloud_accounts:
        return response.bad_request(
            MessageModel(message="Not possible to delete organization due to cloud accounts in use.").dict()
        )

    await helpers.notify_users_about_org_deletion(organization_id=organization_id)

    # delete organization from Keycloak
    org_response = await backend_client.delete(f"/admin/realms/vantage/organizations/{organization_id}")
    if org_response.status_code != status.HTTP_204_NO_CONTENT:
        return response.internal_error(MessageModel(message="Unknown error", **org_response.json()).dict())

    # publish message to RabbitMQ
    try:
        rpc_server_response = await rabbitmq_manager.call(delete_organization_action_payload(organization_id))
    except Exception as err:
        # leave orphan resources in the Vantage infrastructure
        logger.exception(f"Failed to publish message to RabbitMQ: {err}")
    else:
        logger.success(f"Successfully received response from the RPC server: {rpc_server_response}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/my",
    responses={
        200: {"model": list[OrganizationModel], "description": "Organization fetched successfully"},
        500: {"model": MessageModel, "description": "Unknown error, contact support"},
    },
)
async def get_user_organization(decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown())):
    """Get the caller's organization."""
    get_user_response = await backend_client.get(f"/admin/realms/vantage/users/{decoded_token.sub}")
    if get_user_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.precondition_required(MessageModel(message="User not found").dict())
    user_orgs_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/members/{decoded_token.sub}/organizations"
    )
    if user_orgs_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **user_orgs_response.json()))

    if len(user_orgs_response.json()) == 0:
        return response.success([])

    if len(user_orgs_response.json()) > 1:
        return response.internal_error(
            MessageModel(
                message="User belongs to more than one organization",
                **user_orgs_response.json())
        )

    org_id = user_orgs_response.json()[0].get("id")
    org_response = await backend_client.get(f"/admin/realms/vantage/organizations/{org_id}")
    if org_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **org_response.json()))

    org = org_response.json()
    logger.debug(org_response.json())

    organizations = [KeycloakOrganizationModel(
        id=org.get("id"),
        name=org.get("alias"),
        display_name=org.get("attributes").get("display_name", [org.get("name")])[0],
        attributes=org.get("attributes", {}),
        domains=[domain["name"] for domain in org.get("domains", [])],
    )]
    logger.debug(f"Organizations fetched: {organizations}")

    return response.success([OrganizationModel(**org.dict()) for org in organizations])


@router.get(
    "/organizations/members/count",
    responses={
        200: {"description": "Number of members retrieved successfully"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
        500: {"model": MessageModel, "description": "Unknown error, contact support"},
    },
)
async def count_members_of_organization(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
) -> int:
    """Count the numbers of users who belong to the caller's organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    return await fetch_users_count(organization_id)


@router.post(
    "/organizations/members/check-existing",
    responses={
        200: {
            "description": (
                "Successful request. It might contain none or at least one user email in the payload."
            )
        },
        400: {"model": MessageModel, "description": "Organization not found in token"},
    },
    response_model=list[str],
)
async def check_existing_users(
    body: list[str] = Body(
        ...,
        description="A list of user emails",
        examples={
            "email": {
                "summary": "Check if emails match any user on the system.",
                "description": "This example shows how to check if emails match any user on the system.",
                "value": ["foo@example.com", "boo@example.com"],
            }
        },
    ),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Check in a list of users which one of them exist on Keycloak."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    unique_emails = set(body)

    tasks = [
        backend_client.get(
            f"/admin/realms/vantage/organizations/{organization_id}/members",
            params={"search": email}
        )
        for email in unique_emails
    ]
    results: list[httpx.Response] = await asyncio.gather(*tasks)
    return [
        user.get("email") for res in results if res.status_code == status.HTTP_200_OK for user in res.json()
    ]


@router.get(
    "/organizations/members",
    responses={
        200: {"model": UserListModel, "description": "Users retrieved successfully"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
    },
)
async def list_users(
    search: Optional[str] = Query(
        None,
        description="A String contained in username, first or last name, or email",
        examples={
            "email": {
                "summary": "Searches for user by email",
                "description": (
                    "This example shows how to search for a user by its email. Be known that, "
                    "by Matheus Tosta's tests, this input needs to exactly match the user email. Any "
                    "different character won't return the desired user."
                ),
                "value": "foo@boo.com",
            },
            "name": {
                "summary": "Searches for user by name",
                "description": (
                    "This example shows how to search for a user by its name. In this case, the "
                    "supplied string will be used to search in the first name and the last name. "
                    "It can contain any character, including symbols and numbers."
                ),
                "value": "Foo",
            },
        },
    ),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, description="Number of results per page."),
    sort_field: Optional[str] = Depends(helpers.ListUsersFromOrganizationSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:users:read")),
):
    """List all users from an organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    users_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members",
        params={"first": after, "max": per_page, "search": search},
    )
    users = users_response.json()

    users_list = mount_users_list(users)

    if sort_field is not None:
        users_list.users = sorted(
            users_list.users,
            key=lambda user: getattr(user, sort_field) or "",
            reverse=not sort_ascending,
        )
    return response.success(users_list)


@router.get(
    "/organizations/members/{user_id}",
    responses={
        200: {"model": CompleteUserModel, "description": "User retrieved successfully"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
        404: {"model": MessageModel, "description": "User not found"},
    },
)
async def get_user(
    user_id: str = Path(..., description="ID of the user."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:users:read")),
):
    """Get user from an organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    user_exists_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/{user_id}"
    )
    if user_exists_response.status_code != status.HTTP_200_OK:
        return response.not_found({"message": "User not found."})

    user_response = await backend_client.get(f"/admin/realms/vantage/users/{user_id}")
    user_response = user_response.json()

    user = CompleteUserModel(**user_response)
    return response.success(user.dict())


@router.get(
    "/organizations/members/{user_id}/groups",
    responses={
        200: {"model": GroupListModel, "description": "Groups fetched successfully"},
        403: {"model": MessageModel, "description": "Forbidden: missing permissions in token"},
        404: {"model": MessageModel, "description": "User not found by ID"},
    },
)
async def get_groups_attached_to_user(
    user_id: str = Path(..., description="ID of the user."),
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, description="Number of results per page."),
    sort_field: Optional[str] = Depends(helpers.ListGroupsSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Get the groups attached to an user."""
    if decoded_token.sub != user_id:
        if not {"admin:users:read", "admin:groups:read"} <= set(decoded_token.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "WWW-Authenticate": "Bearer",
                },
            )

    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    user_exists_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/{user_id}"
    )
    if user_exists_response.status_code != status.HTTP_200_OK:
        return response.not_found({"message": "User not found."})

    groups_response = await backend_client.get(
        f"/admin/realms/vantage/users/{user_id}/groups",
        params={"first": after, "max": per_page, "briefRepresentation": False},
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

    if sort_field is not None:
        groups = sorted(groups, key=lambda group: group[sort_field], reverse=not sort_ascending)

    return response.success(GroupListModel(groups=groups))


@router.delete(
    "/organizations/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "User deleted successfully"},
        404: {"model": MessageModel, "description": "User not found"},
        500: {"model": MessageModel, "description": "Unknown error. Contact support."},
    },
)
async def delete_user(
    user_id: str = Path(..., description="User ID to be deleted"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:users:delete")),
):
    """Delete user from an organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    user_exists_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/{user_id}"
    )
    if user_exists_response.status_code != status.HTTP_200_OK:
        return response.not_found(MessageModel(message="User not found.", error=user_exists_response.text))

    user_response = await backend_client.delete(f"/admin/realms/vantage/users/{user_id}")

    if user_response.status_code == status.HTTP_204_NO_CONTENT:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        return response.internal_error(
            MessageModel(message="Unknown error. Contact support", **user_response.json())
        )


@router.get(
    "/organizations/idps",
    responses={
        200: {"model": IdPsListModel, "description": "IdPs retrieved successfully"},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
    },
)
async def get_idps(
    sort_field: Optional[str] = Depends(helpers.ListIdPsSortFilterChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:idps:read")),
):
    """Get IdPs enabled for an organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    idps_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/identity-providers"
    )
    if idps_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **idps_response.json()))

    idps = idps_response.json()

    for i, connection in enumerate(idps):
        idps[i] = IdPModel(**connection)

    if sort_field is not None:
        idps = sorted(
            idps,
            key=lambda connection: getattr(connection, sort_field),
            reverse=not sort_ascending,
        )

    return response.success(IdPsListModel(idps=idps))


@router.post(
    "/organizations/idps",
    responses={
        201: {"model": MessageModel, "description": "IdP could be created successfully."},
        400: {"model": MessageModel, "description": "IdP not supported or organization has no domain set."},
        409: {"model": MessageModel, "description": "The organization already have an IdP."},
    },
)
async def create_custom_idp(
    body: Union[AzureIdPModel, GoogleIdPModel, GitHubIdPModel],
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:idps:create")),
):
    """Create an Identity Provider for the requester's organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    org_response = await backend_client.get(f"/admin/realms/vantage/organizations/{organization_id}")
    org = org_response.json()
    organization = KeycloakOrganizationModel(
        id=org.get("id"),
        name=org.get("alias"),
        display_name=org.get("name"),
        attributes=org.get("attributes", {}),
        domains=[domain["name"] for domain in org.get("domains", [])],
    )

    if not organization.domains:
        return response.bad_request(MessageModel(message="Organization has no domain set").dict())
    logger.debug(f"Organization domains: {organization.dict()}")

    body_dict = body.dict()
    idp_name = body_dict.pop("idp_name")
    logger.debug(f"Creating IdP with name: {idp_name} for organization ID: {organization_id}")
    logger.debug(f"Body for IdP creation: {body_dict}")

    config_generator: Callable[..., Dict[str, Any]] = getattr(helpers, f"generate_{idp_name}_config")

    idp_config = config_generator(organization_id=organization_id, **body_dict)
    logger.debug(f"Body for IdP creation: {idp_config}")
    idp_response = await backend_client.post(
        "/admin/realms/vantage/identity-provider/instances",
        json=idp_config
    )
    logger.debug(f"Response from Keycloak: {idp_response.status_code} - {idp_response.content}")

    if idp_response.status_code == status.HTTP_409_CONFLICT:
        return response.conflict(MessageModel(message="The organization already has an IdP"))
    elif idp_response.status_code != status.HTTP_201_CREATED:
        return response.internal_error(MessageModel(message="Unknown error", **idp_response.json()).dict())

    org_idp = await backend_client.post(
        f"/admin/realms/vantage/organizations/{organization_id}/identity-providers",
        content=organization_id
    )
    org_idp.raise_for_status()
    logger.debug(f"Response from Keycloak add to org: {org_idp.status_code} - {org_idp.content}")

    return response.created(MessageModel(message="Successfully created the IdP"))


@router.patch(
    "/organizations/idps",
    responses={
        200: {"model": MessageModel, "description": "IdP updated successfully"},
        404: {"model": MessageModel, "description": "Organization doesn't have an IdP associated."},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
    },
)
async def update_organization_idp(
    body: Union[PatchAzureIdpModel, PatchGitHubIdpModel, PatchGoogleIdpModel],
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:idps:update")),
):
    """Update IdP for the organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    idp_update_body = {"config": {}, "providerId": body.idp_name}

    if body.client_id is not None:
        idp_update_body["config"]["clientId"] = body.client_id
    if body.client_secret is not None:
        idp_update_body["config"]["clientSecret"] = body.client_secret
    if body.idp_name == "azure" and body.app_identifier is not None:
        idp_update_body["config"][
            "tokenUrl"
        ] = f"https://login.microsoftonline.com/${body.app_identifier}/oauth2/v2.0/token"
        idp_update_body["config"][
            "jwksUrl"
        ] = f"https://login.microsoftonline.com/${body.app_identifier}/oauth2/v2.0/token"
        idp_update_body["config"]["issuer"] = f"https://login.microsoftonline.com/${body.app_identifier}/v2.0"
        idp_update_body["config"][
            "authorizationUrl"
        ] = f"https://login.microsoftonline.com/${body.app_identifier}/oauth2/v2.0/authorize"
        idp_update_body["config"][
            "logoutUrl"
        ] = f"https://login.microsoftonline.com/${body.app_identifier}/oauth2/v2.0/logout"
        idp_update_body["providerId"] = "oidc"

    idp_response = await backend_client.put(
        f"/admin/realms/vantage/identity-provider/instances/{organization_id}", json=idp_update_body
    )

    if idp_response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]:
        return response.success(MessageModel(message="Successfully updated the IdP"))
    elif idp_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Organization doesn't have an IdP associated"))
    else:
        return response.internal_error(MessageModel(message="Unknown error", **idp_response.json()))


@router.delete(
    "/organizations/idps",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "IdP deleted successfully"},
        404: {"description": "Organization doesn't have an IdP associated."},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
    },
)
async def delete_organization_idp(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:idps:delete")),
):
    """Delete IdP from the organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    org_idp_response = await backend_client.delete(
        f"/admin/realms/vantage/organizations/{organization_id}/identity-providers/{organization_id}"
    )
    if org_idp_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Organization doesn't have an IdP associated"))

    idp_response = await backend_client.delete(
        f"/admin/realms/vantage/identity-providers/instances/{organization_id}"
    )

    if idp_response.status_code == status.HTTP_204_NO_CONTENT:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    elif idp_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Organization doesn't have an IdP associated"))
    else:
        return response.internal_error(MessageModel(message="Unknown error", **idp_response.json()))


@router.patch(
    "/organizations/members/{user_id}/groups",
    responses={
        200: {
            "model": GroupAttachmentResults,
            "description": "Successfull request. It doesn't mean all input groups were attached. Check the response payload.",  # noqa
        },
        404: {"model": MessageModel, "description": "User not found."},
        400: {"model": MessageModel, "description": "Organization not found in token."},
    },
)
async def assign_groups_to_user(
    body: InputGroupsModel,
    user_id: str = Path(..., description="ID of the user."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:users:update")),
):
    """Assign groups to an user. Input groups already assigned will be marked as success."""
    # check if user belongs to the same orgnanization of the caller
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    user_exists_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/{user_id}"
    )
    if user_exists_response.status_code != status.HTTP_200_OK:
        return response.not_found({"message": "User not found."})

    coroutines = [
        backend_client.put(f"/admin/realms/vantage/users/{user_id}/groups/{group_id}")
        for group_id in body.groups
    ]
    responses = await asyncio.gather(*coroutines)

    response_payload = GroupAttachmentResults()

    for i, user_response in enumerate(responses):
        if user_response.status_code == status.HTTP_204_NO_CONTENT:
            response_payload.successes.append(body.groups[i])
        else:
            response_payload.failures.append(
                {"id": body.groups[i], "code": user_response.status_code, **user_response.json()}
            )

    return response.success(response_payload)


@router.delete(
    "/organizations/members/{user_id}/groups/{group_id}",
    status_code=204,
    responses={
        204: {"description": "Successful request."},
        404: {"model": MessageModel, "description": "Either user or group not found."},
        400: {"model": MessageModel, "description": "Organization not found in token."},
    },
)
async def detach_groups_from_user(
    user_id: str = Path(..., description="ID of the user."),
    group_id: str = Path(..., description="ID of the group."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:users:delete")),
):
    """Detach a group from an user.

    If the user doesn't belong to the group, the endpoint will return 204.
    """
    # check if user belongs to the same orgnanization of the caller
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    user_exists_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/{user_id}"
    )
    if user_exists_response.status_code != status.HTTP_200_OK:
        return response.not_found({"message": "User not found."})

    remove_from_group_response = await backend_client.delete(
        f"/admin/realms/vantage/users/{user_id}/groups/{group_id}"
    )
    if remove_from_group_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="Group not found."))

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/invites/self-check",
    responses={
        200: {
            "model": IsUserInvited,
            "description": "Successful fetch of pending invite for the current user.",
        },
        400: {
            "model": MessageModel,
            "description": "Error fetching the user from keycloak.",
        },
    },
)
async def check_user_has_pending_invites(decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown())):
    """Check if the user has pending invites.

    This endpoint is particularly needed for the case where the user is in the
    organization creation page on the Vantage UI and is invited to an existing
    organization **while** in the mentioned page.
    """
    user_response = await backend_client.get(f"/admin/realms/vantage/users/{decoded_token.sub}")
    if user_response.status_code != status.HTTP_200_OK:
        return response.bad_request(
            MessageModel(message="Error requesting user info.")
        )
    user_data = user_response.json()
    attributes = user_data.get("attributes", {})
    has_inviter_id = "inviter" in attributes
    return IsUserInvited(invited=has_inviter_id)


@router.post(
    "/organizations/invites",
    responses={
        201: {"model": MessageModel, "description": "Invite was created successfully."},
        409: {"model": MessageModel, "description": "Input email already in use."},
        400: {  # noqa: F601
            "model": MessageModel,
            "description": "At least one of the input groups doesn't exist.",
        },
        400: {"model": MessageModel, "description": "Organization not found in token."},  # noqa: F601
        500: {"model": MessageModel, "description": "Internal error when creating invite."},
    },
)
async def invite_user_to_organization(
    body: InviteModel,
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:invites:create")),
):
    """Invite an user to the requester's organization.

    This is done by creating the user on Keycloak and sending an email with the sign in URL.

    This endpoint **won't** verify that the email address exists.
    It's responsibility of the requester to identify and handle failed delivery to non-existing addresses.

    There are many behaviours allowed by this endpoint. They are:

    - Requester supplied groups but no roles
        * Request will proceed successfully if **all** the groups exist.
    - Requester supplied roles but no groups
        * Request will proceed successfully **even** if the roles **don't** exist.
    - Requester supplied groups and roles
        * Request will proceed successfully if **all** the groups exist.
    - Requester supplied user email already in use
        * Request will fail immediately.
    """
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    if await helpers.has_organization_reached_user_limit(organization_id):
        return response.forbidden(MessageModel(message="Organization has reached the user limit").dict())

    logger.debug(f"Inviting user {body.email} to organization {organization_id}")

    is_email_unavailable = await helpers.is_email_allocated_to_other_account(email=body.email)
    logger.debug(f"Email {body.email} is unavailable: {is_email_unavailable}")

    if is_email_unavailable:
        logger.debug(f"Email {body.email} is already in use, returning conflict response")
        return response.conflict(MessageModel(message="Email not available for invitation"))

    # create user on Keycloak
    create_user_body = {
        "username": body.email,
        "email": body.email,
        "enabled": True,
        "groups": body.groups,
        "emailVerified": True,
        "clientRoles": {"default": body.roles},
        "attributes": {"created_at": [str(datetime.now())], "inviter": decoded_token.email},
    }
    logger.debug(f"Creating user with body: {create_user_body}")
    create_user_response = await backend_client.post("/admin/realms/vantage/users", json=create_user_body)

    if create_user_response.status_code == status.HTTP_409_CONFLICT:
        coroutines = [
            helpers.assign_group_to_user_by_group_name(email=body.email, group_name=group_name)
            for group_name in body.groups
        ]
        coroutines.append(helpers.update_inviter_id(body.email, decoded_token.email))
        logger.debug(f"User {body.email} already exists, assigning groups and updating inviter ID")
        await asyncio.gather(*coroutines)
    elif create_user_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return response.bad_request(MessageModel(message="Some of the supplied groups don't exist"))

    # create organization invitation
    invitation_respose = await backend_client.post(
        f"/admin/realms/vantage/organizations/{organization_id}/members/invite-user",
        data={
            "email": body.email,
            "send": False,
            "inviterId": decoded_token.sub,
        },
    )
    if invitation_respose.status_code != status.HTTP_204_NO_CONTENT:
        return response.internal_error(
            MessageModel(message="Internal error when creating invite", **invitation_respose.json())
        )

    return response.created(MessageModel(message="Invite was created successfully"))

@router.post(
    "/organizations/invites/{email}/email",
    responses={
        201: {"model": MessageModel, "description": "Invite was created successfully."},
        500: {  # noqa: F601
            "model": MessageModel,
            "description": "Internal error when checking invited email.",
        },
        500: {"model": MessageModel, "description": "Email could not be sent."},  # noqa: F601
        404: {"model": MessageModel, "description": "Didn't find invite matching the supplied email."},
    },
)
async def resend_invite_email(
    email: str = Path(..., description="Email to which send the invite again."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:invites:create")),
):
    """Send an invite email to a user that has already been invites by using AWS SES."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    invitation_response = await backend_client.post(
        f"/admin/realms/vantage/organizations/{organization_id}/members/invite-user", data={"email": email}
    )

    if invitation_response.status_code != status.HTTP_204_NO_CONTENT:
        return response.internal_error(
            MessageModel(message="Internal error when fetching invitation", **invitation_response.json())
        )
    return response.created(MessageModel(message="Email was sent successfully"))

@router.put(
    "/organizations/members/me",
    responses={
        200: {"model": UserModel, "description": "User profile was updated successfully."},
        404: {"model": MessageModel, "description": "User doesn't exist"},
        500: {"model": MessageModel, "description": "Internal error when updating user profile"},
    },
)
async def update_user_profile(
    body: UpdateUserProfile,
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Update the user profile."""
    user_id = decoded_token.sub
    get_user_response = await backend_client.get(f"/admin/realms/vantage/users/{user_id}")
    if get_user_response.status_code == status.HTTP_404_NOT_FOUND:
        return response.not_found(MessageModel(message="User doesn't exist").dict())
    get_user_response_data: dict[Any, Any] = get_user_response.json()

    # By modifying the get_user_response_data, we avoid the need to make another request to Keycloak
    if body.avatar_url:
        get_user_response_data["attributes"]["picture"] = [body.avatar_url]
    if body.first_name:
        get_user_response_data["firstName"] = body.first_name
    if body.last_name:
        get_user_response_data["lastName"] = body.last_name

    update_user_response = await backend_client.put(
        f"/admin/realms/vantage/users/{user_id}", json=get_user_response_data
    )

    if update_user_response.status_code != status.HTTP_204_NO_CONTENT:
        return response.internal_error(
            MessageModel(
                message="Internal error when updating user profile", **update_user_response.json()
            ).dict()
        )

    return response.success(UserModel(**get_user_response_data).dict())
