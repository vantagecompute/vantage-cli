"""Core module for mapping Keycloak Admin API's schemas or token schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class KeycloakOrganizationModel(BaseModel):

    """Keycloak Organization Model."""

    id: str
    name: str
    display_name: str
    attributes: dict
    url: Optional[str] = Field(str())
    domains: Optional[List[str]] = Field([])


class IdPConfigModel(BaseModel):

    """Model to map the IdP config."""

    client_id: str = Field(..., description="Client ID of the identity provider.", alias="clientId")
