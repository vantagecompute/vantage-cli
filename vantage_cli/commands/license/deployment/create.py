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
"""Create license deployment command."""

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
async def create_license_deployment(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license deployment to create")],
    product_id: Annotated[
        str, typer.Option("--product-id", "-p", help="Product ID for the deployment")
    ],
    environment: Annotated[
        str, typer.Option("--environment", "-e", help="Deployment environment (dev, test, prod)")
    ] = "dev",
    nodes: Annotated[
        Optional[int], typer.Option("--nodes", "-n", help="Number of nodes in the deployment")
    ] = 1,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license deployment"),
    ] = None,
):
    """Create a new license deployment."""
    # Stub data - replace with actual API call
    deployment_data = {
        "deployment_id": "deployment-new-123",
        "name": name,
        "product_id": product_id,
        "environment": environment,
        "nodes": nodes,
        "description": description,
        "status": "created",
        "created_at": "2025-09-10T10:00:00Z",
    }

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=deployment_data,
        resource_name="License Deployment",
        success_message=f"License deployment '{name}' created successfully",
    )
