"""Core module for general helpers utilities."""
from typing import Any, Dict, List

from armasec import TokenPayload
from fastapi import HTTPException, status

from api.body.output import UserListModel, UserModel
from api.identity.management_api import backend_client
from api.utils.logging import logger


def mount_users_list(users: List[Dict[str, Any]]) -> UserListModel:
    """Mount a custom list of users from the Keycloak API response.

    The picture from the attributes takes precedence over the picture from the user object
    because it can be changed by the API accordingly to the user will.
    """
    regular_users = [m for m in users if not m.get("username","").startswith("service-account-")]

    for i, user in enumerate(regular_users):
        first_name = (user.get("firstName") or "").strip()
        last_name = (user.get("lastName") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        user["name"] = full_name if full_name else None
        avatar_url: str = user.get("attributes", {}).get("picture", [None])[0] or user.get("picture", None)
        user.update(avatar_url=avatar_url)
        regular_users[i] = UserModel(**user)
    return UserListModel(users=regular_users)


async def fetch_default_client() -> Dict[str, Any]:
    """Fetch the client whose clientId is 'default' from the Keycloak API."""
    client_response = await backend_client.get(
        "/admin/realms/vantage/clients", params={"clientId": "default"}
    )
    client_payload = client_response.json()
    if not client_response.status_code == status.HTTP_200_OK or len(client_payload) != 1:
        logger.critical(f"Unknown error fetching default client: {client_response.text}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unknown error, contact support")
    default_client = client_payload[0]
    return default_client


def unpack_organization_id_from_token(token: TokenPayload) -> str:
    """Get the organization ID from an access token.

    It expects the following key-value pair in the token:

    "organization": {
        "orgname": {
            "id": "068c6a69-aa62-4ce3-a9d0-da036e2f0001",
            "name": "omnivector",
            "attributes": {
                "created_at": ["123456"],
                "logo": ["https://dummy-logo.com"],
                "owner": ["1cad1f61-0c94-4539-b77e-50ff780e5932"]
            }
        }
    }

    Raise an AssertionError in case the payload in the token is malformed.
    """
    assert token.organization, "Organization payload not in token"

    organization_id = token.organization[next(iter(token.organization))].get("id")
    return organization_id


async def fetch_users_count(tenant: str) -> int:
    """Fetch the number of users from the /users/count endpoint.

    The logic subtracts the number of clients from the total members due to the fact that
    each client is considered a member of the organization because the service account user
    for each particular client is a member of the organization.
    """
    response = await backend_client.get(f"/admin/realms/vantage/organizations/{tenant}/members/count")
    response.raise_for_status()
    total_members = response.json()
    assert isinstance(total_members, int)

    response = await backend_client.get(
        "/admin/realms/vantage/clients", params={"clientId": tenant, "search": True}
    )
    response.raise_for_status()
    num_of_clients = len(response.json())

    return total_members - num_of_clients


def unpack_owner_id_from_token(token: TokenPayload) -> str:
    """Get the owner ID from an access token.

    It expects the following key-value pair in the token:

    "organization": {
        "orgname": {
            "id": "068c6a69-aa62-4ce3-a9d0-da036e2f0001",
            "created_at": ["123456"],
            "logo": ["https://dummy-logo.com"],
            "owner": ["1cad1f61-0c94-4539-b77e-50ff780e5932"]
        }
    }
    """
    assert hasattr(token, "organization"), "Organization payload not in token"  # mypy assertion
    org = token.organization[next(iter(token.organization))]
    owner_id = next(iter(org.get("owner", [])), None)
    return owner_id
