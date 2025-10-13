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
"""List command for cloud credentials."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_command(
    ctx: typer.Context,
    cloud_name: str = typer.Option(None, "--cloud", "-c", help="Filter credentials by cloud name"),
) -> None:
    """List all cloud provider credentials.

    Displays all stored credentials for cloud providers. Optionally filter
    by cloud name to see credentials for a specific cloud.

    Examples:
        List all credentials:
        $ vantage cloud credential list

        List credentials for AWS:
        $ vantage cloud credential list --cloud aws

        Using the alias:
        $ vantage cloud credentials
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.cloud import cloud_sdk
    from vantage_cli.sdk.cloud_credential import cloud_credential_sdk

    # Get cloud ID if cloud name is provided
    cloud_id = None
    if cloud_name:
        cloud = cloud_sdk.get(cloud_name)
        if not cloud:
            ctx.obj.formatter.render_error(
                f"Cloud '{cloud_name}' not found. Use 'vantage cloud list' to see available clouds."
            )
            raise typer.Exit(1)
        cloud_id = cloud.id

    # Get credentials from SDK
    credentials = cloud_credential_sdk.list(cloud_id=cloud_id)

    # Prepare credentials data for output
    credentials_data = []
    for cred in credentials:
        # Get cloud name from ID
        cloud = cloud_sdk.get_by_id(cred.cloud_id)
        cloud_name_display = cloud.name if cloud else cred.cloud_id

        cred_data = {
            "id": cred.id,
            "name": cred.name,
            "type": cred.credential_type,
            "cloud": cloud_name_display,
            "default": cred.default,
            "created": cred.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        credentials_data.append(cred_data)

    # Use UniversalOutputFormatter for consistent list rendering
    ctx.obj.formatter.render_list(
        data=credentials_data,
        resource_name="Cloud Credentials",
        empty_message="No cloud credentials found.",
    )
