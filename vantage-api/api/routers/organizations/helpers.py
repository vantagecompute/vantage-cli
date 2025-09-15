"""Helper functions for the organizations router."""
import re
import unicodedata
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import exists, select
from sqlalchemy.orm import subqueryload

from api.body.output import GroupModel, IdPModel, InvitationModel, UserModel
from api.identity.management_api import backend_client
from api.sql_app import models
from api.sql_app.enums import SubscriptionTierSeats, SubscriptionTypesNames
from api.sql_app.models import SubscriptionModel
from api.sql_app.queries import (
    CHECK_EMAIL_AVAILABILITY_FOR_INVITATION,
    GET_ORGANIZATION_ID_BY_NAME,
)
from api.sql_app.schemas import SubscriptionRow
from api.sql_app.session import create_async_session, keycloak_transaction
from api.utils.email import EMAIL_OPS
from api.utils.helpers import fetch_users_count

sort_field_exception = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Field not available for sorting",
)


class ListUsersFromOrganizationSortFieldChecker:

    """Core class for checking if a given input field is available to sort users by."""

    _model = UserModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


class ListInvitationsSortFieldChecker:

    """Core class for checking if a given input field is available to sort invitations by."""

    _model = InvitationModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


class ListGroupsSortFieldChecker:

    """Core class for checking if a given input field is available to sort groups by."""

    _model = GroupModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


class ListIdPsSortFilterChecker:

    """Core class for checking if a given input field is available to sort IdPs by."""

    _model = IdPModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


def generate_azure_config(
    client_id: str, client_secret: str, app_identifier: str, organization_id: str
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Generate IdP configuration for the Microsoft connection on Keycloak."""
    return {
        "alias": organization_id,
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
            "clientId": client_id,
            "clientSecret": client_secret,
            "tenantId": app_identifier,
            "hideOnLoginPage": "true",
            "acceptsPromptNoneForwardFromClient": "false",
            "disableUserInfo": "false",
            "filteredByClaim": "false",
            "syncMode": "FORCE",
        },
    }


def generate_google_config(
    client_id: str, client_secret: str, organization_id: str
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Generate IdP configuration for the Google IdP on Keycloak."""
    return {
        "alias": organization_id,
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


def generate_github_config(
    client_id: str, client_secret: str, organization_id: str
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Generate IdP configuration for the GitHub IdP on Keycloak."""
    return {
        "alias": organization_id,
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


def parse_org_name(name: str) -> str:
    """Parse organization by removing non-ASCII chars and symbols and replacing white spaces by hyphens."""
    # replace all non-ASCII characters for a similar one.
    # Remove it in case there's no similar. Check
    # tests/routers/organizations/test_organizations_helpers.py::test_parse_organization_name
    # for more information.
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")

    # replace white spaces for hyphens and turn string lower case
    name = re.sub(r"[\s_]+", "-", name)

    # remove symbols and non-alphanumeric characters
    name = re.sub(r"[^\w\s-]", "", name)

    # convert to lowercase and ensure the name neither starts or ends with a hyphen
    name = name.lower().strip("-")

    return name


async def add_admin_user_and_set_up_permissions(admin_user_id: str, org_id: str) -> None:
    """Add the organization creator to the organization itself and grant full admin access."""
    # get the full admin group id
    groups_response = await backend_client.get(
        "/admin/realms/vantage/groups", params={"search": "Full Admin", "exact": True}
    )
    groups_response.raise_for_status()

    group_response_data = groups_response.json()

    if not len(group_response_data) == 1:  # there should be only one group with the name "Full Admin"
        raise ValueError("Expected one group with the name 'Full Admin' but got more than one or none.")

    full_admin_group_id = groups_response.json()[0]["id"]

    # add the organization creator to the Full Admin group
    add_to_group_response = await backend_client.put(
        f"/admin/realms/vantage/users/{admin_user_id}/groups/{full_admin_group_id}"
    )
    add_to_group_response.raise_for_status()

    # add the organization creator to the organization
    add_to_org_response = await backend_client.post(
        f"/admin/realms/vantage/organizations/{org_id}/members/",
        content=admin_user_id
    )
    add_to_org_response.raise_for_status()


async def is_email_allocated_to_other_account(email: str) -> bool:
    """Check if the email is already allocated to another account.

    The idea is to verify if the supplied email has a pending invite to any
    organization or if it is already a member of any organization. If any of
    these conditions are true, then the response is truthy, otherwise it is
    falsey.
    """
    async with keycloak_transaction() as conn:
        record = await conn.fetch(CHECK_EMAIL_AVAILABILITY_FOR_INVITATION, email)
        if len(record) == 0:
            return False
        else:
            return True


async def is_organization_name_available(name: str) -> bool:
    """Check if the organization name is available.

    The idea is to verify if the supplied organization name is already
    allocated to another organization. If this condition is true, then the
    response is truthy, otherwise it is falsey.
    """
    async with keycloak_transaction() as conn:
        record = await conn.fetchrow(GET_ORGANIZATION_ID_BY_NAME, name)
        if record is None:
            return True
        else:
            return False

async def assign_group_to_user_by_group_name(email: str, group_name: str) -> None:
    """Assign a group to a user by the group name."""
    user_response = await backend_client.get(
        "/admin/realms/vantage/users",
        params={
            "briefRepresentation": True,
            "exact": True,
            "email": email,
        },
    )
    user_response.raise_for_status()
    user_id: str = user_response.json()[0].get("id")

    groups_response = await backend_client.get(
        "/admin/realms/vantage/groups", params={"search": group_name, "exact": True}
    )
    groups_response.raise_for_status()

    group_id: str = groups_response.json()[0]["id"]

    add_to_group_response = await backend_client.put(
        f"/admin/realms/vantage/users/{user_id}/groups/{group_id}"
    )
    add_to_group_response.raise_for_status()

async def update_inviter_id(user_email: str, inviter_email: str) -> None:
    """Update the inviter ID for a user by their email address."""
    user_get_response = await backend_client.get(f"/admin/realms/vantage/users?email={user_email}")
    assert user_get_response.status_code == status.HTTP_200_OK, "User not found updating the inviter ID"

    user_data: dict[Any, Any] = user_get_response.json()[0]
    user_data.update({"attributes": {"inviter": inviter_email, "walkthrough": "false"}})

    logger.debug(f"Updating user data with inviter: {user_data}")
    user_put_response = await backend_client.put(
        f"/admin/realms/vantage/users/{user_data.get('id')}",
        json=user_data,
    )

    assert user_put_response.status_code == status.HTTP_204_NO_CONTENT, "Failed to update the inviter ID"

async def has_organization_reached_user_limit(organization_id: str) -> bool:
    """Check if the organization has reached the user limit."""
    number_of_users = await fetch_users_count(organization_id)

    session = await create_async_session(organization_id)
    async with session() as sess:
        query = (
            select(SubscriptionModel)
            .where(SubscriptionModel.organization_id == organization_id)
            .options(subqueryload(SubscriptionModel.subscription_tier))
            .options(subqueryload(SubscriptionModel.subscription_type))
        )
        subscription = (await sess.execute(query)).scalar_one_or_none()
        if subscription is None:
            return True

        subscription_data = SubscriptionRow.from_orm(subscription)
        assert subscription_data.subscription_type is not None  # mypy assertion
        assert subscription_data.subscription_tier is not None  # mypy assertion

    if subscription_data.subscription_type.name == SubscriptionTypesNames.aws:
        if number_of_users >= SubscriptionTierSeats.pro.value:
            return True
    else:
        if subscription_data.subscription_tier.seats is None:
            # it means the organization has the enterprise tier
            return False
        return number_of_users >= subscription_data.subscription_tier.seats
    return False


async def count_members_of_organization(organization_id: str) -> int:
    """Count the number of members in an organization.

    The math behind this is simple: the number of members in an organization
    is the number of users that are members of the organization minus the
    number of clients that are members of the organization. This is because
    Keycloak treats clients as users as each client has a service account
    associated with it.
    """
    number_of_members_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members/count"
    )
    number_of_members_response.raise_for_status()
    number_of_members: int = number_of_members_response.json()

    clients_response = await backend_client.get(
        "/admin/realms/vantage/clients", params={"clientId": organization_id, "search": True}
    )
    clients_response.raise_for_status()

    return number_of_members - len(clients_response.json())


async def notify_users_about_org_deletion(organization_id: str) -> None:
    """Notify users by email when their organization is deleted."""
    number_of_members = await count_members_of_organization(organization_id)
    users_response = await backend_client.get(
        f"/admin/realms/vantage/organizations/{organization_id}/members", params={"max": number_of_members}
    )
    users = users_response.json()

    EMAIL_OPS.send_delete_organization_email(to_addresses=[user.get("email") for user in users])


async def is_cloud_accounts_available_for_deletion(organization_id: str) -> bool:
    """Check if there are any cloud account that has dependent resources.

    Essentially, the function returns False in case there is any cluster
    or any storage resource that has a relation with the cloud account table.
    """
    session = await create_async_session(organization_id)
    async with session() as sess:
        # Check if any cluster depends on a cloud account
        cluster_query = select(exists().where(models.ClusterModel.cloud_account_id.isnot(None)))
        cluster_result = await sess.execute(cluster_query)
        cluster_exists = cluster_result.scalar_one_or_none()

        # Check if any storage depends on a cloud account
        storage_query = select(exists().where(models.StorageModel.cloud_account_id.isnot(None)))
        storage_result = await sess.execute(storage_query)
        storage_exists = storage_result.scalar_one_or_none()

        # If either dependent resources exist, return False
        return not (cluster_exists or storage_exists)
