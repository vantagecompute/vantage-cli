"""Helper functions for the clients router."""
from typing import List, Optional

from fastapi import HTTPException, status

from api.body.output import ClientModel

sort_field_exception = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Field not available for sorting",
)


class ListClientsSortFieldChecker:

    """Core class for checking if a given input field is available to sort clients by."""

    _model = ClientModel

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


_DEFAULT_CLIENTS_LIST_BY_CLIENT_ID = [
    "account",
    "account-console",
    "admin-cli",
    "admin-ops",
    "broker",
    "default",
    "realm-management",
    "security-admin-console",
]


def clean_clients(clients_list: List[ClientModel]) -> List[ClientModel]:
    """Clean up a list of clients.

    The idea is to remove the clients created and managed by Keycloak itself.
    """
    return list(
        filter(lambda client: client.client_id not in _DEFAULT_CLIENTS_LIST_BY_CLIENT_ID, clients_list)
    )
