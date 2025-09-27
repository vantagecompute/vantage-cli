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
"""Get command for cloud credential details."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_command(
    ctx: typer.Context,
    credential_id: str = typer.Argument(..., help="ID of the credential to retrieve"),
    show_secrets: bool = typer.Option(
        False, "--show-secrets", "-s", help="Show sensitive credential data (use with caution)"
    ),
) -> None:
    """Get detailed information about a specific cloud credential.

    Displays comprehensive information about a cloud credential including
    its associated cloud, type, and metadata. Use --show-secrets to display
    sensitive credential data.

    Args:
        ctx: Typer context containing CLI configuration
        credential_id: ID of the credential to retrieve
        show_secrets: Whether to display sensitive credential data

    Examples:
        Get credential details:
        $ vantage cloud credential get abc12345

        Get credential with secrets:
        $ vantage cloud credential get abc12345 --show-secrets
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.cloud import cloud_sdk
    from vantage_cli.sdk.cloud_credential import cloud_credential_sdk

    # Get credential by ID (support partial ID matching)
    all_credentials = cloud_credential_sdk.list()
    credential = None
    for cred in all_credentials:
        if cred.id.startswith(credential_id) or cred.id == credential_id:
            credential = cred
            break

    if not credential:
        ctx.obj.formatter.render_error(
            f"Credential with ID starting with '{credential_id}' not found."
        )
        raise typer.Exit(1)

    # Get cloud name
    cloud = cloud_sdk.get_by_id(credential.cloud_id)
    cloud_name = cloud.name if cloud else credential.cloud_id

    # Prepare credential data for output
    # Use mode='json' to ensure datetime objects are serialized as strings
    cred_data = credential.model_dump(mode="json")
    cred_data["cloud_name"] = cloud_name

    # Hide credentials_data unless --show-secrets is used
    if not show_secrets:
        cred_data["credentials_data"] = "***HIDDEN*** (use --show-secrets to display)"

    # Use UniversalOutputFormatter for consistent get rendering
    ctx.obj.formatter.render_get(
        data=cred_data, resource_name="Cloud Credential", resource_id=credential.id
    )
