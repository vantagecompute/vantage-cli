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
"""Delete command for cloud credentials."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def delete_command(
    ctx: typer.Context,
    credential_id: str = typer.Argument(..., help="ID of the credential to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Delete a cloud provider credential.

    Permanently removes a credential from the system. This action cannot
    be undone.

    Args:
        ctx: Typer context containing CLI configuration
        credential_id: ID of the credential to delete
        force: Skip confirmation prompt

    Examples:
        Delete credential with confirmation:
        $ vantage cloud credential delete abc12345

        Delete without confirmation:
        $ vantage cloud credential delete abc12345 --force
    """
    # Import SDK here to avoid module-level initialization
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

    # Confirm deletion
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete credential '{credential.name}' (ID: {credential.id})?"
        )
        if not confirm:
            ctx.obj.formatter.render_info("Deletion cancelled.")
            raise typer.Exit(0)

    # Delete credential
    deleted = cloud_credential_sdk.delete(credential.id)

    if deleted:
        # Use UniversalOutputFormatter for consistent delete rendering
        ctx.obj.formatter.render_delete(
            resource_name="Cloud Credential",
            resource_id=credential.id,
            success_message=f"Successfully deleted credential '{credential.name}'",
        )
    else:
        ctx.obj.formatter.render_error(f"Failed to delete credential '{credential.name}'")
        raise typer.Exit(1)
