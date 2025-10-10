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
"""List license deployments command."""

from typing import Annotated, Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def list_license_deployments(
    ctx: typer.Context,
    environment: Annotated[
        Optional[str], typer.Option("--environment", "-e", help="Filter by environment")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status")
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of deployments to return"),
    ] = 10,
):
    """List all license deployments."""
    # Stub data - replace with actual API call
    deployments = [
        {
            "deployment_id": "deployment-123",
            "name": "web-app-deployment",
            "product_id": "product-456",
            "environment": "prod",
            "nodes": 5,
            "status": "active",
            "licenses_allocated": 50,
            "licenses_used": 35,
        },
        {
            "deployment_id": "deployment-124",
            "name": "api-deployment",
            "product_id": "product-789",
            "environment": "dev",
            "nodes": 2,
            "status": "inactive",
            "licenses_allocated": 20,
            "licenses_used": 0,
        },
    ]

    # Apply filters
    if environment:
        deployments = [d for d in deployments if d["environment"] == environment]
    if status:
        deployments = [d for d in deployments if d["status"] == status]

    # Apply limit
    filtered_deployments = deployments[:limit] if limit else deployments

    # Use UniversalOutputFormatter for consistent list rendering
    ctx.obj.formatter.render_list(
        data=filtered_deployments,
        resource_name="License Deployments",
    )
