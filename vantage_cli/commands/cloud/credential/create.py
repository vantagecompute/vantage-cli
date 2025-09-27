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
"""Create command for cloud credentials."""

import json

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def create_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name for the credential (e.g., 'AWS Production')"),
    cloud_name: str = typer.Option(
        ..., "--cloud", "-c", help="Cloud provider name (e.g., 'aws', 'gcp', 'azure')"
    ),
    credentials_file: str = typer.Option(
        None, "--file", "-f", help="Path to JSON file containing credential data"
    ),
    credentials_json: str = typer.Option(
        None, "--credentials-json", help="JSON string containing credential data"
    ),
) -> None:
    """Create a new cloud provider credential.

    Creates and stores a new credential for a cloud provider. Credentials
    can be provided via a JSON file or as a JSON string.

    Args:
        ctx: Typer context containing CLI configuration
        name: Human-readable name for the credential
        cloud_name: Name of the cloud provider
        credentials_file: Path to JSON file with credential data
        credentials_json: JSON string with credential data

    Examples:
        Create AWS credential from file:
        $ vantage cloud credential create "AWS Prod" --cloud aws --file aws-creds.json

        Create GCP credential from JSON:
        $ vantage cloud credential create "GCP Dev" --cloud gcp --credentials-json '{"project_id": "my-project"}'
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.cloud import CloudType, cloud_sdk
    from vantage_cli.sdk.cloud_credential import cloud_credential_sdk

    # Validate that either file or json is provided
    if not credentials_file and not credentials_json:
        ctx.obj.formatter.render_error(
            "Either --file or --credentials-json must be provided with credential data."
        )
        raise typer.Exit(1)

    if credentials_file and credentials_json:
        ctx.obj.formatter.render_error(
            "Cannot specify both --file and --credentials-json. Choose one."
        )
        raise typer.Exit(1)

    # Get cloud
    cloud = cloud_sdk.get(cloud_name)
    if not cloud:
        ctx.obj.formatter.render_error(
            f"Cloud '{cloud_name}' not found. Use 'vantage cloud list' to see available clouds."
        )
        raise typer.Exit(1)

    # Load credentials data
    try:
        if credentials_file:
            import pathlib

            cred_path = pathlib.Path(credentials_file)
            if not cred_path.exists():
                ctx.obj.formatter.render_error(f"File not found: {credentials_file}")
                raise typer.Exit(1)
            credentials_data = json.loads(cred_path.read_text())
        else:
            credentials_data = json.loads(credentials_json)
    except json.JSONDecodeError as e:
        ctx.obj.formatter.render_error(f"Invalid JSON: {e}")
        raise typer.Exit(1)

    # Create credential
    # Map cloud name to CloudType
    try:
        # Try direct mapping first
        credential_type = CloudType(cloud.name)
    except ValueError:
        # Fallback to cloud ID if name doesn't match
        try:
            credential_type = CloudType(cloud.id)
        except ValueError:
            ctx.obj.formatter.render_error(
                f"Cannot determine credential type for cloud '{cloud.name}'. "
                f"Cloud type must be one of: {', '.join([ct.value for ct in CloudType])}"
            )
            raise typer.Exit(1)

    credential = cloud_credential_sdk.create(
        name=name,
        credential_type=credential_type,
        cloud_id=cloud.id,
        credentials_data=credentials_data,
    )

    # Prepare credential data for output
    # Use mode='json' to ensure datetime objects are serialized as strings
    cred_data = credential.model_dump(mode="json")
    cred_data["cloud_name"] = cloud.name

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(data=cred_data, resource_name="Cloud Credential")
