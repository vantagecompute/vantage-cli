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
"""Update command for cloud credentials."""

import json
from typing import Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_command(
    ctx: typer.Context,
    credential_id: str = typer.Argument(..., help="ID of the credential to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name for the credential"),
    credentials_json: Optional[str] = typer.Option(
        None, "--credentials-json", "-c", help="New credentials data as JSON string"
    ),
    credentials_file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to JSON file containing new credentials data"
    ),
    set_default: bool = typer.Option(
        False, "--default", "-d", help="Set this credential as the default for its cloud type"
    ),
) -> None:
    """Update an existing cloud credential.

    Updates a credential's name, credentials data, or default status.
    When setting a credential as default, all other credentials of the same
    cloud type will have their default status set to False.

    Args:
        ctx: Typer context containing CLI configuration
        credential_id: ID of the credential to update
        name: New name for the credential
        credentials_json: New credentials data as JSON string
        credentials_file: Path to JSON file with new credentials data
        set_default: Set as default credential for this cloud type

    Examples:
        Update credential name:
        $ vantage cloud credential update abc12345 --name "Production AWS"

        Set as default credential:
        $ vantage cloud credential update abc12345 --default

        Update credentials data:
        $ vantage cloud credential update abc12345 --credentials-json '{"api_key": "new-key"}'

        Update from file:
        $ vantage cloud credential update abc12345 --file credentials.json
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

    # Parse credentials data if provided
    new_credentials_data = None
    if credentials_json and credentials_file:
        ctx.obj.formatter.render_error(
            "Cannot specify both --credentials-json and --file. Choose one."
        )
        raise typer.Exit(1)

    if credentials_json:
        try:
            new_credentials_data = json.loads(credentials_json)
        except json.JSONDecodeError as e:
            ctx.obj.formatter.render_error(f"Invalid JSON in --credentials-json: {e}")
            raise typer.Exit(1)

    if credentials_file:
        try:
            with open(credentials_file, "r") as f:
                new_credentials_data = json.load(f)
        except FileNotFoundError:
            ctx.obj.formatter.render_error(f"File not found: {credentials_file}")
            raise typer.Exit(1)
        except json.JSONDecodeError as e:
            ctx.obj.formatter.render_error(f"Invalid JSON in file {credentials_file}: {e}")
            raise typer.Exit(1)

    # Update the credential
    updated_credential = cloud_credential_sdk.update(
        credential_id=credential.id,
        name=name,
        credentials_data=new_credentials_data,
        set_as_default=set_default,
    )

    if not updated_credential:
        ctx.obj.formatter.render_error(f"Failed to update credential {credential_id}")
        raise typer.Exit(1)

    # Prepare output data
    cred_data = updated_credential.model_dump(mode="json")

    # Get cloud name
    from vantage_cli.sdk.cloud import cloud_sdk

    cloud = cloud_sdk.get_by_id(updated_credential.cloud_id)
    cred_data["cloud_name"] = cloud.name if cloud else updated_credential.cloud_id

    # Hide sensitive credentials_data by default
    cred_data["credentials_data"] = "***HIDDEN***"

    # Render output
    ctx.obj.formatter.render_update(
        data=cred_data,
        resource_name="credential",
        resource_id=updated_credential.id,
        success_message=f"Successfully updated credential '{updated_credential.name}'",
    )
