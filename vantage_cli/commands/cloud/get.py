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
"""Get command for cloud provider details."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_command(
    ctx: typer.Context,
    cloud_name: str = typer.Argument(
        ..., help="Name of the cloud provider (e.g., 'aws', 'localhost', 'gcp')"
    ),
) -> None:
    """Get detailed information about a specific cloud provider.

    Displays comprehensive information about a cloud provider including its
    Vantage provider label, supported substrates, and configuration details.

    Args:
        ctx: Typer context containing CLI configuration
        cloud_name: Name of the cloud provider to retrieve

    Examples:
        Get AWS cloud details:
        $ vantage cloud get aws

        Get localhost cloud details:
        $ vantage cloud get localhost
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.cloud import cloud_sdk

    # Get cloud by name
    cloud = cloud_sdk.get(cloud_name)

    if not cloud:
        ctx.obj.formatter.render_error(
            f"Cloud '{cloud_name}' not found. Use 'vantage cloud list' to see available clouds."
        )
        raise typer.Exit(1)

    # Use UniversalOutputFormatter for consistent get rendering
    ctx.obj.formatter.render_get(
        data=cloud.model_dump(),
        resource_name="Cloud",
        resource_id=cloud.name,
    )
