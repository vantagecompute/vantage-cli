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
"""Get command for cloud provider configurations."""

import typer
from rich import print_json
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.command_utils import should_use_json

from .render import render_cloud_operation_result

console = Console()


def get_command(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the cloud configuration to retrieve")],
) -> None:
    """Get details of a specific cloud configuration.

    Retrieves and displays detailed information about a specific cloud provider
    configuration including credentials, region settings, and connection status.

    Args:
        ctx: The Typer context
        name: Name of the cloud configuration to retrieve
    """
    use_json = should_use_json(ctx)

    # Mock cloud data - in a real implementation, this would fetch from the backend
    mock_cloud = {
        "name": name,
        "provider": "aws",
        "region": "us-west-2",
        "status": "active",
        "created_at": "2025-09-10T05:00:00Z",
        "last_used": "2025-09-10T05:50:00Z",
        "credentials_configured": True,
        "default_region": "us-west-2",
        "available_regions": ["us-west-2", "us-east-1", "eu-west-1"],
    }

    if use_json:
        print_json(data=mock_cloud)
    else:
        render_cloud_operation_result(
            operation="Get Cloud Configuration",
            success=True,
            cloud_name=name,
            details=mock_cloud,
            json_output=False,
        )
