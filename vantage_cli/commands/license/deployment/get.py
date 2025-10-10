# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Get license deployment command."""

from typing import Annotated

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def get_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to retrieve")],
):
    """Get details of a specific license deployment."""
    # Stub data - replace with actual API call
    deployment_data = {
        "deployment_id": deployment_id,
        "name": "web-app-deployment",
        "product_id": "product-456",
        "environment": "prod",
        "nodes": 5,
        "status": "active",
        "description": "Production deployment for web application",
        "created_at": "2025-09-01T09:00:00Z",
        "updated_at": "2025-09-10T10:00:00Z",
        "licenses_allocated": 50,
        "licenses_used": 35,
    }

    # Use UniversalOutputFormatter for consistent get rendering
    ctx.obj.formatter.render_get(
        data=deployment_data,
        resource_name="License Deployment",
    )
