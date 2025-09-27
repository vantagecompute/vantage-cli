# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you cantml:parameter name="redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Base data models and schemas for the Vantage CLI.

This module contains core authentication and CLI context schemas.
Domain-specific schemas have been moved to their respective SDK modules:
- Cluster schemas: vantage_cli.sdk.cluster.schema
- Deployment schemas: vantage_cli.sdk.deployment.schema
- DeploymentApp schemas: vantage_cli.sdk.deployment_app.schema
- Notebook schemas: vantage_cli.sdk.notebook.schema
- Profile schemas: vantage_cli.sdk.profile.schema
- Support ticket schemas: vantage_cli.sdk.support_ticket.schema
"""

from typing import TYPE_CHECKING, Any, Optional

import httpx
from cudo_compute_sdk import CudoComputeSDK
from pydantic import BaseModel
from rich.console import Console

from vantage_cli.config import Settings

if TYPE_CHECKING:
    from vantage_cli.sdk.deployment_app.schema import DeploymentApp

__all__ = [
    # Core/Auth schemas
    "TokenSet",
    "IdentityData",
    "Persona",
    "DeviceCodeData",
    "CliContext",
    # Re-exported for backward compatibility (runtime import only)
    "DeploymentApp",
]


def __getattr__(name: str) -> Any:
    """Lazy import for backward compatibility to avoid circular imports."""
    if name == "DeploymentApp":
        from vantage_cli.sdk.deployment_app.schema import DeploymentApp

        return DeploymentApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class TokenSet(BaseModel):
    """OAuth token set containing access and refresh tokens."""

    access_token: str
    refresh_token: Optional[str] = None


class IdentityData(BaseModel):
    """User identity information extracted from tokens."""

    client_id: str
    email: str
    org_id: str


class Persona(BaseModel):
    """User persona combining token set and identity data."""

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(BaseModel):
    """OAuth device code flow data."""

    device_code: str
    verification_uri_complete: str
    interval: int


class CliContext(BaseModel):
    """CLI context for command execution."""

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    profile: str = "default"
    verbose: bool = False
    json_output: bool = False
    formatter: Optional[Any] = None  # UniversalOutputFormatter (avoid circular import)
    persona: Optional[Persona] = None
    client: Optional[httpx.AsyncClient] = None
    settings: Optional[Settings] = None
    console: Optional[Console] = None
    command_start_time: Optional[float] = None
    rest_client: Optional[Any] = None  # VantageRestApiClient (avoid circular import)
    cudo_sdk: Optional[CudoComputeSDK] = None  # CudoComputeClient (avoid circular import)
