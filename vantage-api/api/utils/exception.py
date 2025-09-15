"""Core module for exception related operations."""
from buzz import Buzz


class AdminAPIError(Buzz):

    """Raise exception when any general error occurs."""


class AuthTokenError(AdminAPIError):

    """Raise exception when there are connection issues with the OIDC provider."""
