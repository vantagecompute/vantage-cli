"""Clients router."""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, Path, Query, status

from api.body.output import ClientListModel, ClientModel, MessageModel
from api.identity.management_api import backend_client
from api.routers.clients.helpers import ListClientsSortFieldChecker, clean_clients
from api.settings import SETTINGS
from api.utils import response
from api.utils.helpers import unpack_organization_id_from_token

router = APIRouter()


@router.get(
    "/clients",
    responses={
        200: {"model": ClientModel, "description": "Client fetched successfully"},
        500: {"model": MessageModel, "description": "Unknown error. Contact support"},
        400: {"model": MessageModel, "description": "Organization not found in token"},
    },
)
async def list_clients(
    after: int = Query(0, ge=0, description="First index to be returned."),
    per_page: int = Query(50, ge=1, description="Number of results per page."),
    client_id: Optional[str] = Query(
        None,
        description=(
            "Search the clients by the client ID. Beware "
            "the distinction between client ID and ID of the client."
        ),
    ),
    sort_field: Optional[str] = Depends(ListClientsSortFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:clients:read")),
):
    """List the available clients for the caller's organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    params = {"first": after, "max": per_page}
    if client_id is not None:
        params.update({"search": True, "clientId": client_id})
    clients_response = await backend_client.get("/admin/realms/vantage/clients", params=params)
    if clients_response.status_code != status.HTTP_200_OK:
        return response.internal_error(MessageModel(message="Unknown error", **clients_response.json()))

    clients = clients_response.json()
    # make sure people can see clients that belong to their organization
    print(clients)
    clients = [client for client in clients if organization_id in client.get("clientId")]
    print(organization_id)
    print(clients)

    clients_list = ClientListModel(clients=clients)
    clients_list.clients = clean_clients(clients_list.clients)

    if sort_field is not None:
        clients_list.clients = sorted(
            clients_list.clients, key=lambda client: getattr(client, sort_field), reverse=not sort_ascending
        )

    return response.success(clients_list)


@router.get(
    "/clients/{id}",
    responses={
        200: {"model": ClientModel, "description": "Client fetched successfully"},
        404: {"model": MessageModel, "description": "Client not found"},
    },
)
async def fetch_client(
    id: str = Path(..., description="ID of the client"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:clients:read")),
):
    """Fetch an existing client.

    This route returns the client secret which is a very sensitive information.
    """
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token"))

    client_response = await backend_client.get(f"/admin/realms/vantage/clients/{id}")
    if client_response.status_code == 404:
        return response.not_found(MessageModel(message=f"Client whose ID is {id} wasn't found."))

    client_payload = client_response.json()
    # make sure people can see clients that belong to their organization
    if organization_id not in client_payload.get("clientId"):
        return response.not_found(MessageModel(message=f"Client whose ID is {id} wasn't found."))

    client_secret_response = await backend_client.get(f"/admin/realms/vantage/clients/{id}/client-secret")

    client_secret_payload = client_secret_response.json()
    client_payload.update(clientSecret=client_secret_payload.get("value"))

    return response.success(ClientModel(**client_payload))
