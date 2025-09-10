"""Data models and schemas for the Vantage CLI."""

from typing import Optional

import httpx
from pydantic import BaseModel

from vantage_cli.config import Settings


class TokenSet(BaseModel):
    """OAuth token set containing access and refresh tokens."""

    access_token: str
    refresh_token: Optional[str] = None


class IdentityData(BaseModel):
    """User identity information extracted from tokens."""

    client_id: str
    email: Optional[str] = None


class Persona(BaseModel):
    """User persona combining token set and identity data."""

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(BaseModel):
    """OAuth device code flow data."""

    device_code: str
    verification_uri_complete: str
    interval: int


class CliContext(BaseModel, arbitrary_types_allowed=True):
    """CLI context for command execution."""

    profile: str = "default"
    verbose: bool = False
    json_output: bool = False
    persona: Optional[Persona] = None
    client: Optional[httpx.AsyncClient] = None
    settings: Optional[Settings] = None
